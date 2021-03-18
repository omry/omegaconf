import re
import sys
import warnings
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

from antlr4 import TerminalNode

from .errors import InterpolationResolutionError

if TYPE_CHECKING:
    from .base import Node  # noqa F401

try:
    from omegaconf.grammar.gen.OmegaConfGrammarLexer import OmegaConfGrammarLexer
    from omegaconf.grammar.gen.OmegaConfGrammarParser import OmegaConfGrammarParser
    from omegaconf.grammar.gen.OmegaConfGrammarParserVisitor import (
        OmegaConfGrammarParserVisitor,
    )

except ModuleNotFoundError:  # pragma: no cover
    print(
        "Error importing OmegaConf's generated parsers, run `python setup.py antlr` to regenerate.",
        file=sys.stderr,
    )
    sys.exit(1)

# Regex matching trailing backslashes.
TRAILING_BACKSLASHES = re.compile("(\\\\)+$")

# Regex matching escaped quotes, for each kind of quote.
# Note that we include *all* backslashes preceding the quote.
ESCAPED_QUOTE = {
    "'": re.compile(r"(\\)+'"),  # escaped single quote
    '"': re.compile(r'(\\)+"'),  # escaped double quote
}


class GrammarVisitor(OmegaConfGrammarParserVisitor):
    def __init__(
        self,
        node_interpolation_callback: Callable[[str], Optional["Node"]],
        resolver_interpolation_callback: Callable[..., Any],
        quoted_string_callback: Callable[[str], str],
        **kw: Dict[Any, Any],
    ):
        """
        Constructor.

        :param node_interpolation_callback: Callback function that is called when
            needing to resolve a node interpolation. This function should take a single
            string input which is the key's dot path (ex: `"foo.bar"`).

        :param resolver_interpolation_callback: Callback function that is called when
            needing to resolve a resolver interpolation. This function should accept
            three keyword arguments: `name` (str, the name of the resolver),
            `args` (tuple, the inputs to the resolver), and `args_str` (tuple,
            the string representation of the inputs to the resolver).

        :param quoted_string_callback: Callback function that is called when needing to
            resolve a quoted string (that may or may not contain interpolations). This
            function should take a single string input which is the content of the quoted
            string (without its enclosing quotes).

        :param kw: Additional keyword arguments to be forwarded to parent class.
        """
        super().__init__(**kw)
        self.node_interpolation_callback = node_interpolation_callback
        self.resolver_interpolation_callback = resolver_interpolation_callback
        self.quoted_string_callback = quoted_string_callback

    def aggregateResult(self, aggregate: List[Any], nextResult: Any) -> List[Any]:
        raise NotImplementedError

    def defaultResult(self) -> List[Any]:
        # Raising an exception because not currently used (like `aggregateResult()`).
        raise NotImplementedError

    def visitConfigKey(self, ctx: OmegaConfGrammarParser.ConfigKeyContext) -> str:
        from ._utils import _get_value

        # interpolation | ID | INTER_KEY
        assert ctx.getChildCount() == 1
        child = ctx.getChild(0)
        if isinstance(child, OmegaConfGrammarParser.InterpolationContext):
            res = _get_value(self.visitInterpolation(child))
            if not isinstance(res, str):
                raise InterpolationResolutionError(
                    f"The following interpolation is used to denote a config key and "
                    f"thus should return a string, but instead returned `{res}` of "
                    f"type `{type(res)}`: {ctx.getChild(0).getText()}"
                )
            return res
        else:
            assert isinstance(child, TerminalNode) and isinstance(
                child.symbol.text, str
            )
            return child.symbol.text

    def visitConfigValue(self, ctx: OmegaConfGrammarParser.ConfigValueContext) -> Any:
        # (toplevelStr | (toplevelStr? (interpolation toplevelStr?)+)) EOF
        # Visit all children (except last one which is EOF)
        vals = [self.visit(c) for c in list(ctx.getChildren())[:-1]]
        n_vals = len(vals)
        assert n_vals > 0

        if n_vals == 1 and isinstance(
            ctx.getChild(0), OmegaConfGrammarParser.InterpolationContext
        ):
            # Single interpolation: return the result "as is".
            return vals[0]

        # Concatenation of multiple components.
        # When a top-level string is followed by an interpolation, we need to un-escape
        # any trailing backslash.
        tokens = []
        for i, (child, val) in enumerate(zip(ctx.getChildren(), vals)):
            if isinstance(child, OmegaConfGrammarParser.ToplevelStrContext):
                if i < n_vals - 1:
                    # Top-level string followed by an interpolation.
                    assert isinstance(
                        ctx.getChild(i + 1), OmegaConfGrammarParser.InterpolationContext
                    )
                    tokens.append(self._unescape_trailing_backslashes(val))
                else:
                    tokens.append(val)
            else:
                tokens.append(str(val))

        return "".join(tokens)

    def visitDictKey(self, ctx: OmegaConfGrammarParser.DictKeyContext) -> Any:
        return self._createPrimitive(ctx)

    def visitDictContainer(
        self, ctx: OmegaConfGrammarParser.DictContainerContext
    ) -> Dict[Any, Any]:
        # BRACE_OPEN (dictKeyValuePair (COMMA dictKeyValuePair)*)? BRACE_CLOSE
        assert ctx.getChildCount() >= 2
        return dict(
            self.visitDictKeyValuePair(ctx.getChild(i))
            for i in range(1, ctx.getChildCount() - 1, 2)
        )

    def visitElement(self, ctx: OmegaConfGrammarParser.ElementContext) -> Any:
        # primitive | listContainer | dictContainer
        assert ctx.getChildCount() == 1
        return self.visit(ctx.getChild(0))

    def visitInterpolation(
        self, ctx: OmegaConfGrammarParser.InterpolationContext
    ) -> Any:
        assert ctx.getChildCount() == 1  # interpolationNode | interpolationResolver
        return self.visit(ctx.getChild(0))

    def visitInterpolationNode(
        self, ctx: OmegaConfGrammarParser.InterpolationNodeContext
    ) -> Optional["Node"]:
        # INTER_OPEN DOT* (configKey (DOT configKey)*)? INTER_CLOSE
        assert ctx.getChildCount() >= 2

        inter_key_tokens = []  # parsed elements of the dot path
        for child in ctx.getChildren():
            if isinstance(child, TerminalNode):
                if child.symbol.type == OmegaConfGrammarLexer.DOT:
                    inter_key_tokens.append(".")  # preserve dots
                else:
                    assert child.symbol.type in (
                        OmegaConfGrammarLexer.INTER_OPEN,
                        OmegaConfGrammarLexer.INTER_CLOSE,
                    )
            else:
                assert isinstance(child, OmegaConfGrammarParser.ConfigKeyContext)
                inter_key_tokens.append(self.visitConfigKey(child))

        inter_key = "".join(inter_key_tokens)
        return self.node_interpolation_callback(inter_key)

    def visitInterpolationResolver(
        self, ctx: OmegaConfGrammarParser.InterpolationResolverContext
    ) -> Any:

        # INTER_OPEN resolverName COLON sequence? BRACE_CLOSE
        assert 4 <= ctx.getChildCount() <= 5

        resolver_name = self.visit(ctx.getChild(1))
        maybe_seq = ctx.getChild(3)
        args = []
        args_str = []
        if isinstance(maybe_seq, TerminalNode):  # means there are no args
            assert maybe_seq.symbol.type == OmegaConfGrammarLexer.BRACE_CLOSE
        else:
            assert isinstance(maybe_seq, OmegaConfGrammarParser.SequenceContext)
            for val, txt in self.visitSequence(maybe_seq):
                args.append(val)
                args_str.append(txt)

        return self.resolver_interpolation_callback(
            name=resolver_name,
            args=tuple(args),
            args_str=tuple(args_str),
        )

    def visitDictKeyValuePair(
        self, ctx: OmegaConfGrammarParser.DictKeyValuePairContext
    ) -> Tuple[Any, Any]:
        from ._utils import _get_value

        assert ctx.getChildCount() == 3  # dictKey COLON element
        key = self.visit(ctx.getChild(0))
        colon = ctx.getChild(1)
        assert (
            isinstance(colon, TerminalNode)
            and colon.symbol.type == OmegaConfGrammarLexer.COLON
        )
        value = _get_value(self.visitElement(ctx.getChild(2)))
        return key, value

    def visitListContainer(
        self, ctx: OmegaConfGrammarParser.ListContainerContext
    ) -> List[Any]:
        # BRACKET_OPEN sequence? BRACKET_CLOSE;
        assert ctx.getChildCount() in (2, 3)
        if ctx.getChildCount() == 2:
            return []
        sequence = ctx.getChild(1)
        assert isinstance(sequence, OmegaConfGrammarParser.SequenceContext)
        return list(val for val, _ in self.visitSequence(sequence))  # ignore raw text

    def visitPrimitive(self, ctx: OmegaConfGrammarParser.PrimitiveContext) -> Any:
        return self._createPrimitive(ctx)

    def visitResolverName(self, ctx: OmegaConfGrammarParser.ResolverNameContext) -> str:
        from ._utils import _get_value

        # (interpolation | ID) (DOT (interpolation | ID))*
        assert ctx.getChildCount() >= 1
        items = []
        for child in list(ctx.getChildren())[::2]:
            if isinstance(child, TerminalNode):
                assert child.symbol.type == OmegaConfGrammarLexer.ID
                items.append(child.symbol.text)
            else:
                assert isinstance(child, OmegaConfGrammarParser.InterpolationContext)
                item = _get_value(self.visitInterpolation(child))
                if not isinstance(item, str):
                    raise InterpolationResolutionError(
                        f"The name of a resolver must be a string, but the interpolation "
                        f"{child.getText()} resolved to `{item}` which is of type "
                        f"{type(item)}"
                    )
                items.append(item)
        return ".".join(items)

    def visitSequence(
        self, ctx: OmegaConfGrammarParser.SequenceContext
    ) -> Generator[Any, None, None]:
        from ._utils import _get_value

        # (element (COMMA element?)*) | (COMMA element?)+
        assert ctx.getChildCount() >= 1

        # DEPRECATED: remove in 2.2 (revert #571)
        def empty_str_warning() -> None:
            txt = ctx.getText()
            warnings.warn(
                f"In the sequence `{txt}` some elements are missing: please replace "
                f"them with empty quoted strings. "
                f"See https://github.com/omry/omegaconf/issues/572 for details.",
                category=UserWarning,
            )

        is_previous_comma = True  # whether previous child was a comma (init to True)
        for child in ctx.getChildren():
            if isinstance(child, OmegaConfGrammarParser.ElementContext):
                # Also preserve the original text representation of `child` so
                # as to allow backward compatibility with old resolvers (registered
                # with `legacy_register_resolver()`). Note that we cannot just cast
                # the value to string later as for instance `null` would become "None".
                yield _get_value(self.visitElement(child)), child.getText()
                is_previous_comma = False
            else:
                assert (
                    isinstance(child, TerminalNode)
                    and child.symbol.type == OmegaConfGrammarLexer.COMMA
                )
                if is_previous_comma:
                    empty_str_warning()
                    yield "", ""
                else:
                    is_previous_comma = True
        if is_previous_comma:
            # Trailing comma.
            empty_str_warning()
            yield "", ""

    def visitSingleElement(
        self, ctx: OmegaConfGrammarParser.SingleElementContext
    ) -> Any:
        # element EOF
        assert ctx.getChildCount() == 2
        return self.visit(ctx.getChild(0))

    def visitToplevelStr(self, ctx: OmegaConfGrammarParser.ToplevelStrContext) -> str:
        # (EVEN_BACKSLASHES | ESC_INTER | TOP_CHAR | TOP_STR)+

        # Concatenate all fragments, un-escaping interpolations.
        tokens = []
        for child in ctx.getChildren():
            txt = child.getText()
            if child.symbol.type == OmegaConfGrammarLexer.ESC_INTER:
                # Un-escape the interpolation, e.g. \${ -> ${ or \\\${ -> \${
                assert len(txt) % 2 == 1
                txt = txt[-(len(txt) + 1) // 2 :]
            tokens.append(txt)

        return "".join(tokens)

    def _createPrimitive(
        self,
        ctx: Union[
            OmegaConfGrammarParser.PrimitiveContext,
            OmegaConfGrammarParser.DictKeyContext,
        ],
    ) -> Any:
        # QUOTED_VALUE |
        # (ID | NULL | INT | FLOAT | BOOL | UNQUOTED_CHAR | COLON | ESC | WS | interpolation)+
        if ctx.getChildCount() == 1:
            child = ctx.getChild(0)
            if isinstance(child, OmegaConfGrammarParser.InterpolationContext):
                return self.visitInterpolation(child)
            assert isinstance(child, TerminalNode)
            symbol = child.symbol
            # Parse primitive types.
            if symbol.type == OmegaConfGrammarLexer.QUOTED_VALUE:
                return self._resolve_quoted_string(symbol.text)
            elif symbol.type in (
                OmegaConfGrammarLexer.ID,
                OmegaConfGrammarLexer.UNQUOTED_CHAR,
                OmegaConfGrammarLexer.COLON,
            ):
                return symbol.text
            elif symbol.type == OmegaConfGrammarLexer.NULL:
                return None
            elif symbol.type == OmegaConfGrammarLexer.INT:
                return int(symbol.text)
            elif symbol.type == OmegaConfGrammarLexer.FLOAT:
                return float(symbol.text)
            elif symbol.type == OmegaConfGrammarLexer.BOOL:
                return symbol.text.lower() == "true"
            elif symbol.type == OmegaConfGrammarLexer.ESC:
                return self._unescape_from_sequence([child])
            elif symbol.type == OmegaConfGrammarLexer.WS:  # pragma: no cover
                # A single WS should have been "consumed" by another token.
                raise AssertionError("WS should never be reached")
            assert False, symbol.type
        # Concatenation of multiple items ==> un-escape the concatenation.
        return self._unescape_from_sequence(ctx.getChildren())

    def _resolve_quoted_string(self, quoted: str) -> str:
        """
        Parse a quoted string.
        """
        # Identify quote type.
        assert len(quoted) >= 2 and quoted[0] == quoted[-1]
        quote_type = quoted[0]

        # Remove enclosing quotes.
        content = quoted[1:-1]

        # Un-escape quotes then trailing backslashes.
        content = self._unescape_quotes(content, quote_type)
        content = self._unescape_trailing_backslashes(content)

        # Parse the string.
        return self.quoted_string_callback(content)

    def _unescape_from_sequence(
        self,
        seq: Iterable[Union[TerminalNode, OmegaConfGrammarParser.InterpolationContext]],
    ) -> str:
        """
        Concatenate all symbols / interpolations in `seq`, unescaping symbols as needed.

        Interpolations are resolved and cast to string *WITHOUT* escaping their result
        (it is assumed that whatever escaping is required was already handled during the
        resolving of the interpolation).
        """
        chrs = []
        for node in seq:
            if isinstance(node, TerminalNode):
                s = node.symbol
                if s.type == OmegaConfGrammarLexer.ESC:
                    chrs.append(s.text[1::2])
                elif s.type == OmegaConfGrammarLexer.ESC_INTER:
                    assert False  # escaped interpolations are handled elsewhere
                else:
                    chrs.append(s.text)
            else:
                assert isinstance(node, OmegaConfGrammarParser.InterpolationContext)
                chrs.append(str(self.visitInterpolation(node)))
        return "".join(chrs)

    def _unescape_quotes(self, expr: str, quote_type: str) -> str:
        """
        Un-escape escaped quotes from an expression.

        Examples:
            abc              -> abc
            abc\'def         -> abc'def
            abc\'\'def\\\'gh -> abc''def\'gh
        """
        pattern = ESCAPED_QUOTE[quote_type]
        match = pattern.search(expr)

        if match is None:
            return expr

        tokens = []
        while match is not None:
            start, stop = match.span()
            size = stop - start
            # An escaped quote is made of an odd number of backslashes followed by a
            # quote, so the total number of matching characters should be even.
            assert size % 2 == 0
            # Add characters before the escaped quote.
            tokens.append(expr[0:start])
            # Add the escaped quote (un-escaping the backslashes, which can be achieved
            # by extracting the proper subset of the string).
            tokens.append(expr[stop - size // 2 : stop])
            # Move on to next match.
            expr = expr[stop:]
            match = pattern.search(expr)

        # Add characters after the last match.
        tokens.append(expr)

        return "".join(tokens)

    def _unescape_trailing_backslashes(self, expr: str) -> str:
        """
        Un-escape trailing backslashes from `expr`.

        Examples:
            abc          -> abc
            abc\\        -> abc\
            abc\\def     -> abc\\def
            abc\\def\\\\ -> abc\\def\\
        """
        match = TRAILING_BACKSLASHES.search(expr)
        if match is None:
            return expr
        start, end = match.span()
        n_backslashes = end - start
        # Sanity check: there should be an even number of backslashes at end of string.
        assert n_backslashes % 2 == 0
        # Un-escaping backslashes <=> removing half of them.
        return expr[0 : start + n_backslashes // 2]
