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

ESC_INTER: ('\\\\')* '\\${';       // \${, \\\${, \\\\\${, ...
EVEN_BACKSLASHES: ESC_BACKSLASH+;  // \\, \\\\, \\\\\\, ...

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

// Quoted values for both types of quotes.
// A quoted value is made of the enclosing quotes, and either:
//   - nothing else
//   - an even number of backslashes (meaning they are escaped)
//   - a sequence of any character, followed by any non-backslash character, and optionally
//     an even number of backslashes (i.e., also escaped)
// Examples (right hand side: expected content of the resulting string, after processing):
//    ""                    -> <empty>
//    '\\'                  -> \
//    "\\\\"                -> \\
//    'abc\\'               -> abc\
//    "abc\"def\\\'ghi\\\\" -> abc"def\\\'ghi\\
QUOTED_VALUE:
      '"' (('\\\\')* | (.)*? ~[\\] ('\\\\')*) '"'     // double quotes
    | '\'' (('\\\\')* | (.)*? ~[\\] ('\\\\')*) '\'';  // single quotes

////////////////////////
// INTERPOLATION_MODE //
////////////////////////

mode INTERPOLATION_MODE;

NESTED_INTER_OPEN: INTER_OPEN WS? -> type(INTER_OPEN), pushMode(INTERPOLATION_MODE);
INTER_COLON: WS? ':' WS? -> type(COLON), mode(VALUE_MODE);
INTER_CLOSE: WS? '}' -> popMode;

DOT: '.';
INTER_ID: ID -> type(ID);

// Interpolation key, may contain any non special character.
// Note that we can allow '$' because the parser does not support interpolations that
// are only part of a key name, i.e., "${foo${bar}}" is not allowed. As a result, it
// is ok to "consume" all '$' characters within the `INTER_KEY` token.
INTER_KEY: ~[\\{}()[\]:. \t'"]+;
