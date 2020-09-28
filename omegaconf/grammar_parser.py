from typing import Any

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext
from antlr4.error.ErrorListener import ErrorListener

from .errors import GrammarParseError

# Import from visitor in order to check the presence of generated grammar files
# files in a single place.
from .grammar_visitor import (  # type: ignore
    OmegaConfGrammarLexer,
    OmegaConfGrammarParser,
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
    error_listener = OmegaConfErrorListener()
    istream = InputStream(value)
    lexer = OmegaConfGrammarLexer(istream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)
    lexer.mode(getattr(OmegaConfGrammarLexer, lexer_mode))
    stream = CommonTokenStream(lexer)
    parser = OmegaConfGrammarParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    # The two lines below could be enabled in the future if we decide to switch
    # to SLL prediction mode. Warning though, it has not been fully tested yet!
    # from antlr4 import PredictionMode
    # parser._interp.predictionMode = PredictionMode.SLL

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
