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
// - Remember to update the documentation (including the tutorial notebook)

parser grammar OmegaConfGrammarParser;
options {tokenVocab = OmegaConfGrammarLexer;}

// Main rules used to parse OmegaConf strings.

configValue: (toplevelStr | (toplevelStr? (interpolation toplevelStr?)+)) EOF;
singleElement: element EOF;

// Top-level string (that does not need to be parsed).
toplevelStr: (ESC | ESC_INTER | TOP_CHAR | TOP_STR)+;

// Elements.

element:
      primitive
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
interpolationNode: INTER_OPEN DOT* (configKey (DOT configKey)*)? INTER_CLOSE;
interpolationResolver: INTER_OPEN resolverName COLON sequence? BRACE_CLOSE;
configKey: interpolation | ID | INTER_KEY;
resolverName: (interpolation | ID) (DOT (interpolation | ID))* ;  // oc.env, myfunc, ns.${x}, ns1.ns2.f

// Primitive types.

primitive:
      QUOTED_VALUE                               // 'hello world', "hello world"
    | (   ID                                     // foo_10
        | NULL                                   // null, NULL
        | INT                                    // 0, 10, -20, 1_000_000
        | FLOAT                                  // 3.14, -20.0, 1e-1, -10e3
        | BOOL                                   // true, TrUe, false, False
        | UNQUOTED_CHAR                          // /, -, \, +, ., $, %, *, @
        | COLON                                  // :
        | ESC                                    // \\, \(, \), \[, \], \{, \}, \:, \=, \ , \\t, \,
        | WS                                     // whitespaces
        | interpolation
      )+;

// Same as `primitive` except that `COLON` and interpolations are not allowed.
dictKey:
      QUOTED_VALUE                               // 'hello world', "hello world"
    | (   ID                                     // foo_10
        | NULL                                   // null, NULL
        | INT                                    // 0, 10, -20, 1_000_000
        | FLOAT                                  // 3.14, -20.0, 1e-1, -10e3
        | BOOL                                   // true, TrUe, false, False
        | UNQUOTED_CHAR                          // /, -, \, +, ., $, %, *, @
        | ESC                                    // \\, \(, \), \[, \], \{, \}, \:, \=, \ , \\t, \,
        | WS                                     // whitespaces
      )+;