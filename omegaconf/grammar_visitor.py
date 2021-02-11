import sys
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

from .errors import GrammarParseError

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


class GrammarVisitor(OmegaConfGrammarParserVisitor):
    def __init__(
        self,
        node_interpolation_callback: Callable[[str], Optional["Node"]],
        resolver_interpolation_callback: Callable[..., Optional["Node"]],
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
            `inputs` (tuple, the inputs to the resolver), and `inputs_str` (tuple,
            the string representation of the inputs to the resolver -- for backward
            compatibility with resolvers registered with `legacy_register_resolver()`).

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
        aggregate.append(nextResult)
        return aggregate

    def defaultResult(self) -> List[Any]:
        return []

    def visitConfigKey(self, ctx: OmegaConfGrammarParser.ConfigKeyContext) -> str:
        from ._utils import _get_value

        # interpolation | ID | LIST_INDEX
        assert ctx.getChildCount() == 1
        child = ctx.getChild(0)
        if isinstance(child, OmegaConfGrammarParser.InterpolationContext):
            res = _get_value(self.visitInterpolation(child))
            if not isinstance(res, str):
                raise GrammarParseError(
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

    def visitConfigValue(
        self, ctx: OmegaConfGrammarParser.ConfigValueContext
    ) -> Union[str, Optional["Node"]]:
        assert ctx.getChildCount() == 2  # toplevel EOF
        assert isinstance(ctx.getChild(0), OmegaConfGrammarParser.ToplevelContext)
        return self.visitToplevel(ctx.getChild(0))

    def visitDictValue(
        self, ctx: OmegaConfGrammarParser.DictValueContext
    ) -> Dict[Any, Any]:
        # BRACE_OPEN (dictKeyValuePair (COMMA dictKeyValuePair)*)? BRACE_CLOSE
        assert ctx.getChildCount() >= 2
        return dict(
            self.visitDictKeyValuePair(ctx.getChild(i))
            for i in range(1, ctx.getChildCount() - 1, 2)
        )

    def visitElement(self, ctx: OmegaConfGrammarParser.ElementContext) -> Any:
        # primitive | listValue | dictValue
        assert ctx.getChildCount() == 1
        return self.visit(ctx.getChild(0))

    def visitInterpolation(
        self, ctx: OmegaConfGrammarParser.InterpolationContext
    ) -> Optional["Node"]:
        from .base import Node  # noqa F811

        assert ctx.getChildCount() == 1  # interpolationNode | interpolationResolver
        ret = self.visit(ctx.getChild(0))
        assert ret is None or isinstance(ret, Node)
        return ret

    def visitInterpolationNode(
        self, ctx: OmegaConfGrammarParser.InterpolationNodeContext
    ) -> Optional["Node"]:
        # INTER_OPEN DOT* configKey (DOT configKey)* INTER_CLOSE
        assert ctx.getChildCount() >= 3

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
    ) -> Optional["Node"]:
        from ._utils import _get_value

        # INTER_OPEN (interpolation | ID) COLON sequence? BRACE_CLOSE;
        resolver_name = None
        inputs = []
        inputs_str = []
        for child in ctx.getChildren():
            if (
                isinstance(child, TerminalNode)
                and child.symbol.type == OmegaConfGrammarLexer.ID
            ):
                assert resolver_name is None
                resolver_name = child.symbol.text
            elif isinstance(child, OmegaConfGrammarParser.InterpolationContext):
                assert resolver_name is None
                resolver_name = _get_value(self.visitInterpolation(child))
                if not isinstance(resolver_name, str):
                    raise GrammarParseError(
                        f"The name of a resolver must be a string, but the interpolation "
                        f"{child.getText()} resolved to `{resolver_name}` which is of type "
                        f"{type(resolver_name)}"
                    )
            elif isinstance(child, OmegaConfGrammarParser.SequenceContext):
                assert resolver_name is not None
                for val, txt in self.visitSequence(child):
                    inputs.append(val)
                    inputs_str.append(txt)
            else:
                assert isinstance(child, TerminalNode)

        assert resolver_name is not None
        return self.resolver_interpolation_callback(
            name=resolver_name,
            inputs=tuple(inputs),
            inputs_str=tuple(inputs_str),
        )

    def visitDictKeyValuePair(
        self, ctx: OmegaConfGrammarParser.DictKeyValuePairContext
    ) -> Tuple[Any, Any]:
        from ._utils import _get_value

        assert ctx.getChildCount() == 3  # ID COLON element
        key_node = ctx.getChild(0)
        assert (
            isinstance(key_node, TerminalNode)
            and key_node.symbol.type == OmegaConfGrammarLexer.ID
        )
        key = key_node.symbol.text
        value = _get_value(self.visitElement(ctx.getChild(2)))
        return key, value

    def visitListValue(self, ctx: OmegaConfGrammarParser.ListValueContext) -> List[Any]:
        # BRACKET_OPEN sequence? BRACKET_CLOSE;
        assert ctx.getChildCount() in (2, 3)
        if ctx.getChildCount() == 2:
            return []
        sequence = ctx.getChild(1)
        assert isinstance(sequence, OmegaConfGrammarParser.SequenceContext)
        return list(val for val, _ in self.visitSequence(sequence))  # ignore raw text

    def visitPrimitive(self, ctx: OmegaConfGrammarParser.PrimitiveContext) -> Any:
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
                return self._unescape([child])
            elif symbol.type == OmegaConfGrammarLexer.WS:  # pragma: no cover
                # A single WS should have been "consumed" by another token.
                raise AssertionError("WS should never be reached")
            assert False, symbol.type
        # Concatenation of multiple items ==> un-escape the concatenation.
        return self._unescape(ctx.getChildren())

    def visitSequence(
        self, ctx: OmegaConfGrammarParser.SequenceContext
    ) -> Generator[Any, None, None]:
        from ._utils import _get_value

        assert ctx.getChildCount() >= 1  # element (COMMA element)*
        for i, child in enumerate(ctx.getChildren()):
            if i % 2 == 0:
                assert isinstance(child, OmegaConfGrammarParser.ElementContext)
                # Also preserve the original text representation of `child` so
                # as to allow backward compatibility with old resolvers (registered
                # with `legacy_register_resolver()`). Note that we cannot just cast
                # the value to string later as for instance `null` would become "None".
                yield _get_value(self.visitElement(child)), child.getText()
            else:
                assert (
                    isinstance(child, TerminalNode)
                    and child.symbol.type == OmegaConfGrammarLexer.COMMA
                )

    def visitSingleElement(
        self, ctx: OmegaConfGrammarParser.SingleElementContext
    ) -> Any:
        # element EOF
        assert ctx.getChildCount() == 2
        return self.visit(ctx.getChild(0))

    def visitToplevel(
        self, ctx: OmegaConfGrammarParser.ToplevelContext
    ) -> Union[str, Optional["Node"]]:
        # toplevelStr | (toplevelStr? (interpolation toplevelStr?)+)
        vals = self.visitChildren(ctx)
        if len(vals) == 1 and isinstance(
            ctx.getChild(0), OmegaConfGrammarParser.InterpolationContext
        ):
            from .base import Node  # noqa F811

            # Single interpolation: return the resulting node "as is".
            ret = vals[0]
            assert ret is None or isinstance(ret, Node), ret
            return ret
        # Concatenation of multiple components.
        return "".join(map(str, vals))

    def visitToplevelStr(self, ctx: OmegaConfGrammarParser.ToplevelStrContext) -> str:
        # (ESC | ESC_INTER | TOP_CHAR | TOP_STR)+
        return self._unescape(ctx.getChildren())

    def _resolve_quoted_string(self, quoted: str) -> str:
        """
        Parse a quoted string.
        """
        # Identify quote type.
        assert len(quoted) >= 2 and quoted[0] == quoted[-1]
        quote_type = quoted[0]
        assert quote_type in ["'", '"']

        # Un-escape quotes and backslashes within the string (the two kinds of
        # escapable characters in quoted strings). We do it in two passes:
        #   1. Replace `\"` with `"` (and similarly for single quotes)
        #   2. Replace `\\` with `\`
        # The order is important so that `\\"` is replaced with an escaped quote `\"`.
        # We also remove the start and end quotes.
        esc_quote = f"\\{quote_type}"
        quoted_content = (
            quoted[1:-1].replace(esc_quote, quote_type).replace("\\\\", "\\")
        )

        # Parse the string.
        return self.quoted_string_callback(quoted_content)

    def _unescape(
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
                    chrs.append(s.text[1:])
                else:
                    chrs.append(s.text)
            else:
                assert isinstance(node, OmegaConfGrammarParser.InterpolationContext)
                chrs.append(str(self.visitInterpolation(node)))
        return "".join(chrs)
