import sys

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from .vendor.antlr4.ParserRuleContext import ParserRuleContext


Antlr4ParserRuleContext: TypeAlias = ParserRuleContext  # type: ignore[valid-type]
