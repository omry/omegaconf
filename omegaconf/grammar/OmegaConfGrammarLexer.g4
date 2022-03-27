// Regenerate lexer and parser by running 'python setup.py antlr' at project root.
// See `OmegaConfGrammarParser.g4` for some important information regarding how to
// properly maintain this grammar.

lexer grammar OmegaConfGrammarLexer;

// Re-usable fragments.
fragment CHAR: [a-zA-Z];
fragment DIGIT: [0-9];
fragment INT_UNSIGNED: '0' | [1-9] (('_')? DIGIT)*;
fragment ESC_BACKSLASH: '\\\\';  // escaped backslash

/////////////////////////////
// DEFAULT_MODE (TOPLEVEL) //
/////////////////////////////

TOP_INTER_OPEN: INTER_OPEN -> type(INTER_OPEN), pushMode(INTERPOLATION_MODE);

// Regular string: anything that does not contain any $ and does not end with \
// (this ensures this rule will not consume characters required to recognize other tokens).
ANY_STR: ~[$]* ~[\\$];

// Escaped interpolation: '\${', optionally preceded by an even number of \
ESC_INTER: ESC_BACKSLASH* '\\${';

// Backslashes that *may* be escaped (even number).
TOP_ESC: ESC_BACKSLASH+;

// Other backslashes that will not need escaping (odd number due to not matching the previous rule).
BACKSLASHES: '\\'+ -> type(ANY_STR);

// The dollar sign must be singled out so that we can recognize interpolations.
DOLLAR: '$' -> type(ANY_STR);


////////////////
// VALUE_MODE //
////////////////

mode VALUE_MODE;

INTER_OPEN: '${' WS? -> pushMode(INTERPOLATION_MODE);
BRACE_OPEN: '{' WS? -> pushMode(VALUE_MODE);  // must keep track of braces to detect end of interpolation
BRACE_CLOSE: WS? '}' -> popMode;
QUOTE_OPEN_SINGLE: '\'' -> pushMode(QUOTED_SINGLE_MODE);
QUOTE_OPEN_DOUBLE: '"' -> pushMode(QUOTED_DOUBLE_MODE);

COMMA: WS? ',' WS?;
BRACKET_OPEN: '[' WS?;
BRACKET_CLOSE: WS? ']';
COLON: WS? ':' WS?;

// Numbers.

fragment POINT_FLOAT: INT_UNSIGNED '.' | INT_UNSIGNED? '.' DIGIT (('_')? DIGIT)*;
fragment EXPONENT_FLOAT: (INT_UNSIGNED | POINT_FLOAT) [eE] [+-]? DIGIT (('_')? DIGIT)*;
FLOAT: [+-]? (POINT_FLOAT | EXPONENT_FLOAT | [Ii][Nn][Ff] | [Nn][Aa][Nn]);
INT: [+-]? INT_UNSIGNED;

// Other reserved keywords.

BOOL:
      [Tt][Rr][Uu][Ee]      // TRUE
    | [Ff][Aa][Ll][Ss][Ee]; // FALSE

NULL: [Nn][Uu][Ll][Ll];

UNQUOTED_CHAR: [/\-\\+.$%*@?|];  // other characters allowed in unquoted strings
ID: (CHAR|'_') (CHAR|DIGIT|'_'|'-')*;
ESC: (ESC_BACKSLASH | '\\(' | '\\)' | '\\[' | '\\]' | '\\{' | '\\}' |
      '\\:' | '\\=' | '\\,' | '\\ ' | '\\\t')+;
WS: [ \t]+;


////////////////////////
// INTERPOLATION_MODE //
////////////////////////

mode INTERPOLATION_MODE;

NESTED_INTER_OPEN: INTER_OPEN WS? -> type(INTER_OPEN), pushMode(INTERPOLATION_MODE);
INTER_COLON: WS? ':' WS? -> type(COLON), mode(VALUE_MODE);
INTER_CLOSE: WS? '}' -> popMode;

DOT: '.';
INTER_BRACKET_OPEN: '[' -> type(BRACKET_OPEN);
INTER_BRACKET_CLOSE: ']' -> type(BRACKET_CLOSE);
INTER_ID: ID -> type(ID);

// Interpolation key, may contain any non special character.
// Note that we can allow '$' because the parser does not support interpolations that
// are only part of a key name, i.e., "${foo${bar}}" is not allowed. As a result, it
// is ok to "consume" all '$' characters within the `INTER_KEY` token.
INTER_KEY: ~[\\{}()[\]:. \t'"]+;


////////////////////////
// QUOTED_SINGLE_MODE //
////////////////////////

mode QUOTED_SINGLE_MODE;

// This mode is very similar to `DEFAULT_MODE` except for the handling of quotes.

QSINGLE_INTER_OPEN: INTER_OPEN -> type(INTER_OPEN), pushMode(INTERPOLATION_MODE);
MATCHING_QUOTE_CLOSE: '\'' -> popMode;

// Regular string: anything that does not contain any $ *or quote* and does not end with \
QSINGLE_STR: ~['$]* ~['\\$] -> type(ANY_STR);

QSINGLE_ESC_INTER: ESC_INTER -> type(ESC_INTER);

// Escaped quote (optionally preceded by an even number of backslashes).
QSINGLE_ESC_QUOTE: ESC_BACKSLASH* '\\\'' -> type(ESC);

QUOTED_ESC: ESC_BACKSLASH+;
QSINGLE_BACKSLASHES: '\\'+ -> type(ANY_STR);
QSINGLE_DOLLAR: '$' -> type(ANY_STR);


////////////////////////
// QUOTED_DOUBLE_MODE //
////////////////////////

mode QUOTED_DOUBLE_MODE;

// Same as `QUOTED_SINGLE_MODE` but for double quotes.

QDOUBLE_INTER_OPEN: INTER_OPEN -> type(INTER_OPEN), pushMode(INTERPOLATION_MODE);
QDOUBLE_CLOSE: '"' -> type(MATCHING_QUOTE_CLOSE), popMode;

QDOUBLE_STR: ~["$]* ~["\\$] -> type(ANY_STR);
QDOUBLE_ESC_INTER: ESC_INTER -> type(ESC_INTER);
QDOUBLE_ESC_QUOTE: ESC_BACKSLASH* '\\"' -> type(ESC);
QDOUBLE_ESC: ESC_BACKSLASH+ -> type(QUOTED_ESC);
QDOUBLE_BACKSLASHES: '\\'+ -> type(ANY_STR);
QDOUBLE_DOLLAR: '$' -> type(ANY_STR);
