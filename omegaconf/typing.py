try:
    from typing import TypeAlias
except ImportError:
    # Python <= 3.9
    from typing_extensions import TypeAlias

from .vendor.antlr4.ParserRuleContext import ParserRuleContext


Antlr4ParserRuleContext: TypeAlias = ParserRuleContext  # type: ignore[valid-type]
