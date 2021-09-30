// Regenerate parser by running 'python setup.py antlr' at project root.

// Maintenance guidelines when modifying this grammar:
//
// - Consider whether the regex pattern `SIMPLE_INTERPOLATION_PATTERN` found in
//   `grammar_parser.py` should be updated as well.
//
// - Update Hydra's grammar accordingly.
//
// - Keep up-to-date the comments in the visitor (in `grammar_visitor.py`)
//   that contain grammar excerpts (within each `visit...()` method).
//
// - Remember to update the documentation (including the tutorial notebook as
//   well as grammar.rst)

parser grammar OmegaConfGrammarParser;
options {tokenVocab = OmegaConfGrammarLexer;}

// Main rules used to parse OmegaConf strings.

configValue: text EOF;
singleElement: element EOF;


// Composite text expression (may contain interpolations).

text: (interpolation | ANY_STR | ESC | ESC_INTER | TOP_ESC | QUOTED_ESC)+;


// Elements.

element:
      primitive
    | quotedValue
    | listContainer
    | dictContainer
;


// Data structures.

listContainer: BRACKET_OPEN sequence? BRACKET_CLOSE;                         // [], [1,2,3], [a,b,[1,2]]
dictContainer: BRACE_OPEN (dictKeyValuePair (COMMA dictKeyValuePair)*)? BRACE_CLOSE;  // {}, {a:10,b:20}
dictKeyValuePair: dictKey COLON element;
sequence: (element (COMMA element?)*) | (COMMA element?)+;


// Interpolations.

interpolation: interpolationNode | interpolationResolver;

interpolationNode:
      INTER_OPEN
      DOT*                                                     // relative interpolation?
      (configKey | BRACKET_OPEN configKey BRACKET_CLOSE)       // foo, [foo]
      (DOT configKey | BRACKET_OPEN configKey BRACKET_CLOSE)*  // .foo, [foo], .foo[bar], [foo].bar[baz]
      INTER_CLOSE;
interpolationResolver: INTER_OPEN resolverName COLON sequence? BRACE_CLOSE;
configKey: interpolation | ID | INTER_KEY;
resolverName: (interpolation | ID) (DOT (interpolation | ID))* ;  // oc.env, myfunc, ns.${x}, ns1.ns2.f


// Primitive types.

// Ex: "hello world", 'hello ${world}'
quotedValue: (QUOTE_OPEN_SINGLE | QUOTE_OPEN_DOUBLE) text? MATCHING_QUOTE_CLOSE;

primitive:
    (   ID                                     // foo_10
      | NULL                                   // null, NULL
      | INT                                    // 0, 10, -20, 1_000_000
      | FLOAT                                  // 3.14, -20.0, 1e-1, -10e3
      | BOOL                                   // true, TrUe, false, False
      | UNQUOTED_CHAR                          // /, -, \, +, ., $, %, *, @, ?, |
      | COLON                                  // :
      | ESC                                    // \\, \(, \), \[, \], \{, \}, \:, \=, \ , \\t, \,
      | WS                                     // whitespaces
      | interpolation
    )+;

// Same as `primitive` except that `COLON` and interpolations are not allowed.
dictKey:
    (   ID                                     // foo_10
      | NULL                                   // null, NULL
      | INT                                    // 0, 10, -20, 1_000_000
      | FLOAT                                  // 3.14, -20.0, 1e-1, -10e3
      | BOOL                                   // true, TrUe, false, False
      | UNQUOTED_CHAR                          // /, -, \, +, ., $, %, *, @, ?, |
      | ESC                                    // \\, \(, \), \[, \], \{, \}, \:, \=, \ , \\t, \,
      | WS                                     // whitespaces
    )+;