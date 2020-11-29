// Regenerate parser by running 'python setup.py antlr' at project root.

// Maintenance guidelines when modifying this grammar:
//
// - For initial testing of the parsing abilities of the modified grammer before
//   writing all the support visitor code, change the test
//        `tests/test_interpolation.py::test_all_interpolations`
//   by setting `dbg_test_access_only = True`, and run it. You will also probably
//   need to comment / hijack the code accesssing the visitor. Tests that expect
//   errors raised from the visitor will obviously fail.
//
// - Update Hydra's grammar accordingly, and if you added more cases to the test
//   mentioned above, copy the latest version of `TEST_CONFIG_DATA` to Hydra (see
//   Hydra's test: `tests/test_overrides_parser.py::test_omegaconf_interpolations`).

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
    | listValue
    | dictValue
;

// Data structures.

listValue: BRACKET_OPEN sequence? BRACKET_CLOSE;                          // [], [1,2,3], [a,b,[1,2]]
dictValue: BRACE_OPEN (dictKeyValuePair (COMMA dictKeyValuePair)*)? BRACE_CLOSE;  // {}, {a:10,b:20}
dictKeyValuePair: ID COLON element;
sequence: element (COMMA element)*;

// Interpolations.

interpolation: interpolationNode | interpolationResolver;
interpolationNode: INTER_OPEN DOT* configKey (DOT configKey)* INTER_CLOSE;
interpolationResolver: INTER_OPEN (interpolation | ID) COLON sequence? BRACE_CLOSE;
configKey: interpolation | ID | LIST_INDEX;

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
