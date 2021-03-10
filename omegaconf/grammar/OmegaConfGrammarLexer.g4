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

ESC_INTER: '\\${';
TOP_ESC: ESC_BACKSLASH+ -> type(ESC);

// The backslash and dollar characters must not be grouped with others, so that
// we can properly detect the tokens above.
TOP_CHAR: [\\$];
TOP_STR: ~[\\$]+;  // anything else

////////////////
// VALUE_MODE //
////////////////

mode VALUE_MODE;

INTER_OPEN: '${' WS? -> pushMode(INTERPOLATION_MODE);
BRACE_OPEN: '{' WS? -> pushMode(VALUE_MODE);  // must keep track of braces to detect end of interpolation
BRACE_CLOSE: WS? '}' -> popMode;

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

UNQUOTED_CHAR: [/\-\\+.$%*@];  // other characters allowed in unquoted strings
ID: (CHAR|'_') (CHAR|DIGIT|'_')*;
ESC: (ESC_BACKSLASH | '\\(' | '\\)' | '\\[' | '\\]' | '\\{' | '\\}' |
      '\\:' | '\\=' | '\\,' | '\\ ' | '\\\t')+;
WS: [ \t]+;

QUOTED_VALUE:
      '\'' ('\\\''|.)*? '\'' // Single quotes, can contain escaped single quote : /'
    | '"' ('\\"'|.)*? '"' ;  // Double quotes, can contain escaped double quote : /"

////////////////////////
// INTERPOLATION_MODE //
////////////////////////

mode INTERPOLATION_MODE;

NESTED_INTER_OPEN: INTER_OPEN WS? -> type(INTER_OPEN), pushMode(INTERPOLATION_MODE);
INTER_COLON: WS? ':' WS? -> type(COLON), mode(VALUE_MODE);
INTER_CLOSE: WS? '}' -> popMode;

DOT: '.';
INTER_ID: ID -> type(ID);
INTER_KEY: ~[\\${}()[\]:. \t'"]+;  // interpolation key, may contain any non special character
