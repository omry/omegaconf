import re
import threading
from typing import Any, Tuple

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext
from antlr4.error.ErrorListener import ErrorListener

from .errors import GrammarParseError

# Import from visitor in order to check the presence of generated grammar files
# files in a single place.
from .grammar_visitor import (  # type: ignore
    OmegaConfGrammarLexer,
    OmegaConfGrammarParser,
)

# Used to cache grammar objects to avoid re-creating them on each call to `parse()`.
_grammar_cache = None

# Lock to ensure we do not use cached objects in parallel threads.
_cache_lock = threading.Lock()

# Build regex pattern to efficiently identify typical interpolations.
# See test `test_match_simple_interpolation_pattern` for examples.
_config_key = r"[$\w]+"  # foo, $0, $bar, $foo_$bar123$
_key_maybe_brackets = f"{_config_key}|\\[{_config_key}\\]"  # foo, [foo], [$bar]
_node_access = f"\\.{_key_maybe_brackets}"  # .foo, [foo], [$bar]
_node_path = f"(\\.)*({_key_maybe_brackets})({_node_access})*"  # [foo].bar, .foo[bar]
_node_inter = f"\\${{\\s*{_node_path}\\s*}}"  # node interpolation ${foo.bar}
_id = "[a-zA-Z_]\\w*"  # foo, foo_bar, abc123
_resolver_name = f"({_id}(\\.{_id})*)?"  # foo, ns.bar3, ns_1.ns_2.b0z
_arg = "[a-zA-Z_0-9/\\-\\+.$%*@]+"  # string representing a resolver argument
_args = f"{_arg}(\\s*,\\s*{_arg})*"  # list of resolver arguments
_resolver_inter = f"\\${{\\s*{_resolver_name}\\s*:\\s*{_args}?\\s*}}"  # ${foo:bar}
_inter = f"({_node_inter}|{_resolver_inter})"  # any kind of interpolation
_outer = "([^$]|\\$(?!{))+"  # any character except $ (unless not followed by {)
SIMPLE_INTERPOLATION_PATTERN = re.compile(
    f"({_outer})?({_inter}({_outer})?)+$", flags=re.ASCII
)


class OmegaConfErrorListener(ErrorListener):  # type: ignore
    def syntaxError(
        self,
        recognizer: Any,
        offending_symbol: Any,
        line: Any,
        column: Any,
        msg: Any,
        e: Any,
    ) -> None:
        raise GrammarParseError(str(e) if msg is None else msg) from e

    def reportAmbiguity(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: Any,
        stopIndex: Any,
        exact: Any,
        ambigAlts: Any,
        configs: Any,
    ) -> None:
        raise GrammarParseError("ANTLR error: Ambiguity")  # pragma: no cover

    def reportAttemptingFullContext(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: Any,
        stopIndex: Any,
        conflictingAlts: Any,
        configs: Any,
    ) -> None:
        # Note: for now we raise an error to be safe. However this is mostly a
        # performance warning, so in the future this may be relaxed if we need
        # to change the grammar in such a way that this warning cannot be
        # avoided (another option would be to switch to SLL parsing mode).
        raise GrammarParseError(
            "ANTLR error: Attempting Full Context"
        )  # pragma: no cover

    def reportContextSensitivity(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: Any,
        stopIndex: Any,
        prediction: Any,
        configs: Any,
    ) -> None:
        raise GrammarParseError("ANTLR error: ContextSensitivity")  # pragma: no cover


def parse(
    value: str, parser_rule: str = "configValue", lexer_mode: str = "DEFAULT_MODE"
) -> ParserRuleContext:
    """
    Parse interpolated string `value` (and return the parse tree).
    """
    global _grammar_cache

    lexer_mode_index = getattr(OmegaConfGrammarLexer, lexer_mode)
    istream = InputStream(value)

    use_cache = _cache_lock.acquire(blocking=False)
    try:
        if use_cache:
            if _grammar_cache is None:
                lexer, tokens, parser = _get_grammar_objects(istream, lexer_mode_index)
                _grammar_cache = lexer, tokens, parser
            else:
                lexer, tokens, parser = _grammar_cache
                lexer.inputStream = istream
                lexer.mode(lexer_mode_index)
                tokens.setTokenSource(lexer)
                parser.reset()

        else:
            # If another thread is already using the cache, then we simply re-create
            # new temporary objects (instead of waiting for the lock to be released).
            lexer, tokens, parser = _get_grammar_objects(istream, lexer_mode_index)

        try:
            return getattr(parser, parser_rule)()
        except Exception as exc:
            if type(exc) is Exception and str(exc) == "Empty Stack":
                # This exception is raised by antlr when trying to pop a mode while
                # no mode has been pushed. We convert it into an `GrammarParseError`
                # to facilitate exception handling from the caller.
                raise GrammarParseError("Empty Stack")
            else:
                raise

    finally:
        if use_cache:
            _cache_lock.release()


def _get_grammar_objects(
    istream: InputStream, lexer_mode_index: Any
) -> Tuple[OmegaConfGrammarLexer, CommonTokenStream, OmegaConfGrammarParser]:
    """
    Obtain the lexer, its token stream and the parser, ready to parse the input stream.
    """
    error_listener = OmegaConfErrorListener()
    lexer = OmegaConfGrammarLexer(istream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)
    lexer.mode(lexer_mode_index)
    tokens = CommonTokenStream(lexer)
    parser = OmegaConfGrammarParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    # The two lines below could be enabled in the future if we decide to switch
    # to SLL prediction mode. Warning though, it has not been fully tested yet!
    # from antlr4 import PredictionMode
    # parser._interp.predictionMode = PredictionMode.SLL

    return lexer, tokens, parser
