import math
import re
import threading
import time
from contextlib import nullcontext
from typing import Any, Callable, List, Optional, Set, Tuple

from pytest import mark, param, raises, warns

from omegaconf import (
    AnyNode,
    Container,
    DictConfig,
    ListConfig,
    OmegaConf,
    _utils,
    grammar_parser,
    grammar_visitor,
)
from omegaconf.errors import (
    GrammarParseError,
    InterpolationKeyError,
    InterpolationResolutionError,
    UnsupportedInterpolationType,
)
from omegaconf.typing import Antlr4ParserRuleContext

TAB = "\t"  # to be used in raw strings, e.g. `fr"C:\{TAB}foo"`

# Characters that are not allowed by the grammar in config key names.
INVALID_CHARS_IN_KEY_NAMES = r"""\{}()[].:"' """
UNQUOTED_SPECIAL = r"/-\+.$%*@?|"  # special characters allowed in unquoted strings

# A fixed config that may be used (but not modified!) by tests.
BASE_TEST_CFG = OmegaConf.create(
    {
        # Standard data types.
        "str": "hi",
        "int": 123,
        "float": 1.2,
        "bytes": b"binary",
        "dict": {"a": 0, "b": {"c": 1}},
        "list": [x - 1 for x in range(11)],
        "null": None,
        # Special cases.
        "x@y": 123,  # @ in name
        "$x$y$z$": 456,  # $ in name (beginning, middle and end)
        "0": 0,  # integer name
        "FalsE": {"TruE": True},  # bool name
        "None": {"null": 1},  # null-like name
        "1": {"2": 12},  # dot-path with int keys
        # Used in nested interpolations.
        "str_test": "test",
        "ref_str": "str",
        "options": {"a": "A", "b": "B"},
        "choice": "a",
        "rel_opt": ".options",
    }
)


# Parameters for tests of the "singleElement" rule when there is no interpolation.
# Each item is a tuple with three elements:
#   - The id of the test.
#   - The expression to be evaluated.
#   - The expected result, that may be an exception. If it is a `GrammarParseError` then
#     it is assumed that the parsing will fail. If it is another kind of exception then
#     it is assumed that the parsing will succeed, but this exception will be raised when
#     visiting (= evaluating) the parse tree. If the expected behavior is for the parsing
#     to succeed, but a `GrammarParseError` to be raised when visiting it, then set the
#     expected result to the pair `(None, GrammarParseError)`.
PARAMS_SINGLE_ELEMENT_NO_INTERPOLATION: List[Tuple[str, str, Any]] = [
    # Special keywords.
    ("null", "null", None),
    ("true", "TrUe", True),
    ("false", "falsE", False),
    ("true_false", "true_false", "true_false"),
    # Integers.
    ("int", "123", 123),
    ("int_pos", "+123", 123),
    ("int_neg", "-123", -123),
    ("int_underscore", "1_000", 1000),
    ("int_bad_underscore_1", "1_000_", "1_000_"),
    ("int_bad_underscore_2", "1__000", "1__000"),
    ("int_bad_underscore_3", "_1000", "_1000"),
    ("int_bad_zero_start", "007", "007"),
    # Floats.
    ("float", "1.1", 1.1),
    ("float_no_int", ".1", 0.1),
    ("float_no_decimal", "1.", 1.0),
    ("float_minus", "-.2", -0.2),
    ("float_plus", "+.2", 0.2),
    ("float_underscore_1", "1.1_1", 1.11),
    ("float_underscore_2", "1_1_2.1", 112.1),
    ("float_bad_1", "1.+2", "1.+2"),
    ("float_bad_2", r"1\.2", r"1\.2"),
    ("float_bad_3", "1.2_", "1.2_"),
    ("float_bad_4", "1__1.2", "1__1.2"),
    ("float_exp_1", "-1e2", -100.0),
    ("float_exp_2", "+1E-2", 0.01),
    ("float_exp_3", "1_0e1_0", 10e10),
    ("float_exp_4", "1.07e+2", 107.0),
    ("float_exp_5", "1e+03", 1000.0),
    ("float_exp_bad_1", "e-2", "e-2"),
    ("float_exp_bad_2", "01e2", "01e2"),
    ("float_exp_bad_3", "0_e0", "0_e0"),
    ("float_inf", "inf", math.inf),
    ("float_plus_inf", "+inf", math.inf),
    ("float_minus_inf", "-inf", -math.inf),
    ("float_nan", "nan", math.nan),
    ("float_plus_nan", "+nan", math.nan),
    ("float_minus_nan", "-nan", math.nan),
    # Unquoted strings.
    # Note: raw strings do not allow trailing \, adding a space and stripping it.
    (
        "str_legal",
        (r" a" + UNQUOTED_SPECIAL + r"\\ ").strip(),
        (r" a" + UNQUOTED_SPECIAL + r"\ ").strip(),
    ),
    ("str_illegal_1", "a,=b", GrammarParseError),
    ("str_illegal_2", f"{chr(200)}", GrammarParseError),
    ("str_illegal_3", f"{chr(129299)}", GrammarParseError),
    ("str_dot", ".", "."),
    ("str_dollar", "$", "$"),
    ("str_colon", ":", ":"),
    ("str_ws_1", "hello world", "hello world"),
    ("str_ws_2", "a b\tc  \t\t  d", "a b\tc  \t\t  d"),
    ("str_esc_ws_1", r"\ hello\ world\ ", " hello world "),
    ("str_esc_ws_2", rf"\ \{TAB}\{TAB}", f" {TAB}{TAB}"),
    ("str_esc_comma", r"hello\, world", "hello, world"),
    ("str_esc_colon", r"a\:b", "a:b"),
    ("str_esc_equal", r"a\=b", "a=b"),
    ("str_esc_parentheses", r"\(foo\)", "(foo)"),
    ("str_esc_brackets", r"\[foo\]", "[foo]"),
    ("str_esc_braces", r"\{foo\}", "{foo}"),
    ("str_esc_backslash", r" \ ".strip(), r" \ ".strip()),
    ("str_backslash_noesc", r"ab\cd", r"ab\cd"),
    ("str_esc_illegal_1", r"\#", GrammarParseError),
    ("str_esc_illegal_2", r""" \'\" """.strip(), GrammarParseError),
    # Quoted strings.
    ("str_quoted_single", "'!@#$%^&*|()[]:.,\"'", '!@#$%^&*|()[]:.,"'),
    ("str_quoted_double", '"!@#$%^&*|()[]:.,\'"', "!@#$%^&*|()[]:.,'"),
    ("str_quoted_outer_ws_single", "'  a \t'", "  a \t"),
    ("str_quoted_outer_ws_double", '"  a \t"', "  a \t"),
    ("str_quoted_int", "'123'", "123"),
    ("str_quoted_null", "'null'", "null"),
    ("str_quoted_bool", "['truE', \"FalSe\"]", ["truE", "FalSe"]),
    ("str_quoted_list", "'[a,b, c]'", "[a,b, c]"),
    ("str_quoted_dict", '"{a:b, c: d}"', "{a:b, c: d}"),
    ("str_quoted_backslash_noesc_single", r"'a\b'", r"a\b"),
    ("str_quoted_backslash_noesc_double", r'"a\b"', r"a\b"),
    ("str_quoted_concat_bad_2", "'Hi''there'", GrammarParseError),
    ("str_quoted_too_many_1", "''a'", GrammarParseError),
    ("str_quoted_too_many_2", "'a''", GrammarParseError),
    ("str_quoted_too_many_3", "''a''", GrammarParseError),
    ("str_quoted_trailing_esc_1", r"'abc\\'", r" abc\ ".strip()),
    ("str_quoted_trailing_esc_2", r"'abc\\\\'", r" abc\\ ".strip()),
    ("str_quoted_no_esc_single_1", r"'abc\def'", r"abc\def"),
    ("str_quoted_no_esc_single_2", r"'abc\\def'", r"abc\\def"),
    ("str_quoted_no_esc_single_3", r"'\\\abc\def'", r"\\\abc\def"),
    ("str_quoted_no_esc_dollar_single", r"'abc\\$$'", r"abc\\$$"),
    ("str_quoted_no_esc_double_1", r'"abc\def"', r"abc\def"),
    ("str_quoted_no_esc_double_2", r'"abc\\def"', r"abc\\def"),
    ("str_quoted_no_esc_double_3", r'"\\\abc\def"', r"\\\abc\def"),
    ("str_quoted_no_esc_dollar_double", r'"abc\\$$"', r"abc\\$$"),
    ("str_quoted_bad_1", r'"abc\"', GrammarParseError),
    ("str_quoted_bad_2", r'"abc\\\"', GrammarParseError),
    ("str_quoted_esc_quote_single_1", r"'abc\'def'", "abc'def"),
    ("str_quoted_esc_quote_single_2", r"'abc\\\'def'", r"abc\'def"),
    ("str_quoted_esc_quote_single_3", r"'abc\\\\\'def'", r"abc\\'def"),
    ("str_quoted_esc_quote_single_4", r"'a\'b\'cdef\\\''", r"a'b'cdef\'"),
    ("str_quoted_esc_quote_single_bad", r"'abc\\'def'", GrammarParseError),
    ("str_quoted_esc_quote_double_1", r'"abc\"def"', 'abc"def'),
    ("str_quoted_esc_quote_double_2", r'"abc\\\"def"', r"abc\"def"),
    ("str_quoted_esc_quote_double_3", r'"abc\\\\\"def"', r'abc\\"def'),
    ("str_quoted_esc_quote_double_4", r'"a\"b\"cdef\\\""', r'a"b"cdef\"'),
    ("str_quoted_esc_quote_double_bad", r'"abc\\"def"', GrammarParseError),
    ("str_quoted_empty", "''", ""),
    ("str_quoted_basic", "'a'", "a"),
    ("str_quoted_tmp_1", r"'\a'", r"\a"),
    ("str_quoted_tmp_2", r"'a\'", GrammarParseError),
    ("str_quoted_inside_quote_different", "'\"'", '"'),
    ("str_quoted_inside_quote_same", r"'\''", "'"),
    ("str_quoted_extra_quote", r"'c:\\''", GrammarParseError),
    # Lists and dictionaries.
    ("list", "[0, 1]", [0, 1]),
    (
        "dict",
        "{x: 1, a: b, y: 1e2, null2: 0.1, true3: false, inf4: true}",
        {"x": 1, "a": "b", "y": 100.0, "null2": 0.1, "true3": False, "inf4": True},
    ),
    (
        "dict_unquoted_key",
        rf"{{a0-null-1-3.14-NaN- {TAB}-true-False-{UNQUOTED_SPECIAL}\(\)\[\]\{{\}}\:\=\ \{TAB}\,:0}}",
        {
            rf"a0-null-1-3.14-NaN- {TAB}-true-False-{UNQUOTED_SPECIAL}()[]{{}}:= {TAB},": 0
        },
    ),
    (
        "dict_quoted",
        "{0: 1, 'a': 'b', 1.1: 1e2, null: 0.1, true: false, -inf: true}",
        GrammarParseError,
    ),
    (
        "structured_mixed",
        "[10,str,3.14,true,false,inf,[1,2,3], 'quoted', \"quoted\", 'a,b,c']",
        [
            10,
            "str",
            3.14,
            True,
            False,
            math.inf,
            [1, 2, 3],
            "quoted",
            "quoted",
            "a,b,c",
        ],
    ),
    ("dict_int_key", "{0: 0}", {0: 0}),
    ("dict_float_key", "{1.1: 0}", {1.1: 0}),
    ("dict_null_key", "{null: 0}", {None: 0}),
    ("dict_nan_like_key", "{'nan': 0}", GrammarParseError),
    ("dict_list_as_key", "{[0]: 1}", GrammarParseError),
    (
        "dict_bool_key",
        "{true: true, false: 'false'}",
        {True: True, False: "false"},
    ),
    ("empty_dict", "{}", {}),
    ("empty_list", "[]", []),
    (
        "structured_deep",
        "{null0: [0, 3.14, false], true1: {a: [0, 1, 2], b: {}}}",
        {"null0": [0, 3.14, False], "true1": {"a": [0, 1, 2], "b": {}}},
    ),
]

# Parameters for tests of the "singleElement" rule when there are interpolations.
PARAMS_SINGLE_ELEMENT_WITH_INTERPOLATION = [
    # Node interpolations.
    ("dict_access", "${dict.a}", 0),
    ("list_access", "${list.0}", -1),
    ("dict_access_getitem", "${dict[a]}", 0),
    ("list_access_getitem", "${list[0]}", -1),
    ("getitem_first_1", "${[dict].a}", 0),
    ("getitem_first_2", "${[list][0]}", -1),
    ("dict_access_deep_1", "${dict.b.c}", 1),
    ("dict_access_deep_2", "${dict[b].c}", 1),
    ("dict_access_deep_3", "${dict.b[c]}", 1),
    ("dict_access_deep_4", "${dict[b][c]}", 1),
    ("list_access_underscore", "${list.1_0}", 9),
    ("list_access_bad_negative", "${list.-1}", InterpolationKeyError),
    ("dict_access_list_like_1", "${0}", 0),
    ("dict_access_list_like_2", "${1.2}", 12),
    ("bool_like_keys", "${FalsE.TruE}", True),
    ("null_like_key_ok", "${None.null}", 1),
    ("null_like_key_bad_case", "${NoNe.null}", InterpolationKeyError),
    ("null_like_key_quoted_1", "${'None'.'null'}", GrammarParseError),
    ("null_like_key_quoted_2", "${'None.null'}", GrammarParseError),
    ("dotpath_bad_type", "${dict.${float}}", (None, InterpolationResolutionError)),
    ("at_in_key", "${x@y}", 123),
    ("dollar_in_key", "${$x$y$z$}", 456),
    # Interpolations in dictionaries.
    ("dict_interpolation_value", "{hi: ${str}, int: ${int}}", {"hi": "hi", "int": 123}),
    ("dict_interpolation_key", "{${str}: 0, ${null}: 1", GrammarParseError),
    # Interpolations in lists.
    ("list_interpolation", "[${str}, ${int}]", ["hi", 123]),
    # Interpolations in unquoted strings.
    ("str_dollar_and_inter", "$$${str}", "$$hi"),
    ("str_inter", "hi_${str}", "hi_hi"),
    ("str_esc_illegal_3", r"\${foo\}", GrammarParseError),
    # Interpolations in quoted strings.
    ("str_quoted_inter", "'${null}'", "None"),
    ("str_quoted_esc_single_1", r"'ab\'cd\'\'${str}'", "ab'cd''hi"),
    ("str_quoted_esc_single_2", r"""'\\\${foo}'""", r"\${foo}"),
    ("str_quoted_esc_single_3", r"""'\\a_${str}'""", r"\\a_hi"),
    ("str_quoted_esc_single_4", r"""'a_${str}\\'""", r" a_hi\ ".strip()),
    ("str_quoted_esc_double_1", r'"ab\"cd\"\"${str}"', 'ab"cd""hi'),
    ("str_quoted_esc_double_2", r'''"\\\${foo}"''', r"\${foo}"),
    ("str_quoted_esc_double_3", r'''"\\a_${str}"''', r"\\a_hi"),
    ("str_quoted_esc_double_4", r'''"a_${str}\\"''', r" a_hi\ ".strip()),
    ("str_quoted_other_quote_double", """'double"'""", 'double"'),
    ("str_quoted_other_quote_single", '''"single'"''', "single'"),
    ("str_quoted_concat_bad_1", '"Hi "${str}', GrammarParseError),
    ("str_quoted_nested", "'${test:\"b\"}'", "b"),
    ("str_quoted_nested_esc_quotes", "'${test:'b'}'", "b"),
    ("str_quoted_esc_inter", r"""'\${test:"b"}'""", '${test:"b"}'),
    ("str_quoted_esc_inter_and_quotes", r"'\${test:\'b\'}'", "${test:'b'}"),
    ("str_quoted_esc_inter_nested_single_1", r"""'${test:'\${str}'}'""", "${str}"),
    ("str_quoted_esc_inter_nested_single_2", r"""'${test:'\\${str}'}'""", r"\hi"),
    ("str_quoted_esc_inter_nested_single_3", r"""'${test:'\\\${str}'}'""", r"\${str}"),
    ("str_quoted_esc_inter_nested_double_1", r'''"${test:"\${str}"}"''', "${str}"),
    ("str_quoted_esc_inter_nested_double_2", r'''"${test:"\\${str}"}"''', r"\hi"),
    ("str_quoted_esc_inter_nested_double_3", r'''"${test:"\\\${str}"}"''', r"\${str}"),
    ("str_quoted_error_inside_quotes", "'${missing_brace'", GrammarParseError),
    # Whitespaces.
    ("ws_inter_node_outer", "${ \tdict.a  \t}", 0),
    ("ws_inter_node_around_dot", "${dict .\ta}", GrammarParseError),
    ("ws_inter_node_inside_id", "${d i c t.a}", GrammarParseError),
    ("ws_inter_res_outer", "${\t test:foo\t  }", "foo"),
    ("ws_inter_res_around_colon", "${test\t  : \tfoo}", "foo"),
    ("ws_inter_res_inside_id", "${te st:foo}", GrammarParseError),
    ("ws_inter_res_inside_args", "${test:f o o}", "f o o"),
    ("ws_inter_res_namespace", "${ns1 .\t ns2 . test:0}", GrammarParseError),
    ("ws_inter_res_no_args", "${test: \t}", []),
    ("ws_list", "${test:[\t a,   b,  ''\t  ]}", ["a", "b", ""]),
    ("ws_dict", "${test:{\t a   : 1\t  , b:  \t''}}", {"a": 1, "b": ""}),
    ("ws_quoted_single", "${test:  \t'foo'\t }", "foo"),
    ("ws_quoted_double", '${test:  \t"foo"\t }', "foo"),
    # Nested interpolations.
    ("nested_simple", "${${ref_str}}", "hi"),
    ("nested_select", "${options.${choice}}", "A"),
    ("nested_select_getitem", "${options[${choice}]}", "A"),
    ("nested_relative", "${${rel_opt}.b}", "B"),
    ("str_quoted_nested_deep_single", r"'AB${test:'CD${test:'EF'}GH'}'", "ABCDEFGH"),
    ("str_quoted_nested_deep_double", r'"AB${test:"CD${test:"EF"}GH"}"', "ABCDEFGH"),
    ("str_quoted_nested_deep_mixed", r'''"AB${test:'CD${test:"EF"}GH'}"''', "ABCDEFGH"),
    (
        "str_quoted_issue_615",
        r'${test:"The root drive is: \\${str}:\\"}',
        r" The root drive is: \hi:\ ".strip(),
    ),
    # Resolver interpolations.
    ("no_args", "${test:}", []),
    ("space_in_args", "${test:a, b c}", ["a", "b c"]),
    ("list_as_input", "${test:[a, b], 0, [1.1]}", [["a", "b"], 0, [1.1]]),
    ("dict_as_input", "${test:{a: 1.1, b: b}}", {"a": 1.1, "b": "b"}),
    ("dict_as_input_quotes", "${test:{'a': 1.1, b: b}}", GrammarParseError),
    ("dict_typo_colons", "${test:{a: 1.1, b:: b}}", {"a": 1.1, "b": ": b"}),
    ("missing_resolver", "${MiSsInG_ReSoLvEr:0}", UnsupportedInterpolationType),
    ("at_in_resolver", "${y@z:}", GrammarParseError),
    ("ns_resolver", "${ns1.ns2.test:123}", 123),
    # Nested resolvers.
    ("nested_resolver", "${${str_test}:a, b, c}", ["a", "b", "c"]),
    ("nested_deep", "${test:${${test:${ref_str}}}}", "hi"),
    (
        "nested_resolver_combined_illegal",
        "${some_${resolver}:a, b, c}",
        GrammarParseError,
    ),
    ("nested_args", "${test:${str}, ${null}, ${int}}", ["hi", None, 123]),
    # Invalid resolver names.
    ("int_resolver_quoted", "${'0':1,2,3}", GrammarParseError),
    ("int_resolver_noquote", "${0:1,2,3}", GrammarParseError),
    ("float_resolver_quoted", "${'1.1':1,2,3}", GrammarParseError),
    ("float_resolver_noquote", "${1.1:1,2,3}", GrammarParseError),
    ("float_resolver_exp", "${1e1:1,2,3}", GrammarParseError),
    ("inter_float_resolver", "${${float}:1,2,3}", (None, InterpolationResolutionError)),
    # NaN as dictionary key (a resolver is used here to output only the key).
    ("dict_nan_key_1", "${first:{nan: 0}}", math.nan),
    ("dict_nan_key_2", "${first:{${test:nan}: 0}}", GrammarParseError),
]

# Parameters for tests of the "configValue" rule (may contain interpolations).
PARAMS_CONFIG_VALUE = [
    # String interpolations (top-level).
    ("str_top_basic", "bonjour ${str}", "bonjour hi"),
    ("str_top_quotes_single_1", "'bonjour ${str}'", "'bonjour hi'"),
    (
        "str_top_quotes_single_2",
        "'Bonjour ${str}', I said.",
        "'Bonjour hi', I said.",
    ),
    ("str_top_quotes_double_1", '"bonjour ${str}"', '"bonjour hi"'),
    (
        "str_top_quotes_double_2",
        '"Bonjour ${str}", I said.',
        '"Bonjour hi", I said.',
    ),
    ("str_top_missing_end_quote_single", "'${str}", "'hi"),
    ("str_top_missing_end_quote_double", '"${str}', '"hi'),
    ("str_top_missing_start_quote_double", '${str}"', 'hi"'),
    ("str_top_missing_start_quote_single", "${str}'", "hi'"),
    ("str_top_middle_quote_single", "I'd like ${str}", "I'd like hi"),
    ("str_top_middle_quote_double", 'I"d like ${str}', 'I"d like hi'),
    ("str_top_middle_quotes_single", "I like '${str}'", "I like 'hi'"),
    ("str_top_middle_quotes_double", 'I like "${str}"', 'I like "hi"'),
    (
        "str_top_any_char",
        r"${str} " + UNQUOTED_SPECIAL + r"^!#&})][({,;",
        r"hi " + UNQUOTED_SPECIAL + r"^!#&})][({,;",
    ),
    ("str_top_esc_inter", r"Esc: \${str}", "Esc: ${str}"),
    ("str_top_esc_inter_wrong_1", r"Wrong: $\{str\}", r"Wrong: $\{str\}"),
    ("str_top_esc_inter_wrong_2", r"Wrong: \${str\}", r"Wrong: ${str\}"),
    ("str_top_esc_backslash_1", r"Esc: \\${str}", r"Esc: \hi"),
    ("str_top_esc_backslash_2", r"Esc: \\\\${str}", r"Esc: \\hi"),
    ("str_top_quoted_braces_wrong", r"Wrong: \{${str}\}", r"Wrong: \{hi\}"),
    ("str_top_leading_dollars", r"$$${str}", "$$hi"),
    ("str_top_trailing_dollars", r"${str}$$$$", "hi$$$$"),
    ("str_top_leading_escapes_1", r"\\\\\${str}", r"\\${str}"),
    ("str_top_leading_escapes_2", r"\\\\ \${str}", r"\\\\ ${str}"),
    ("str_top_middle_escapes_1", r"abc\\\\\${str}", r"abc\\${str}"),
    ("str_top_middle_escapes_2", r"abc\\\\ \${str}", r"abc\\\\ ${str}"),
    ("str_top_trailing_escapes", r" ${str}\\\ ".strip(), r" hi\\\ ".strip()),
    ("str_top_concat_interpolations", "${null}${float}", "None1.2"),
    ("str_top_issue_617", r""" ${test: "hi\\" }"} """, r" hi\"} "),
    # Whitespaces.
    ("ws_toplevel", "  \tab  ${str} cd  ${int}\t", "  \tab  hi cd  123\t"),
    # Unmatched braces.
    ("missing_brace_1", "${test:${str}", GrammarParseError),
    ("missing_brace_2", "${${test:str}", GrammarParseError),
    ("extra_brace", "${str}}", "hi}"),
]


def parametrize_from(
    data: List[Tuple[str, str, Any]]
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Utility function to create PyTest parameters from the lists above"""
    return mark.parametrize(
        ["definition", "expected"],
        [param(definition, expected, id=key) for key, definition, expected in data],
    )


class TestOmegaConfGrammar:
    """
    Test most grammar constructs.

    Each method in this class tests the validity of expressions in a specific
    setting. For instance, `test_single_element_no_interpolation()` tests the
    "singleElement" parsing rule on expressions that do not contain interpolations
    (which allows for faster tests without using any config object).

    Tests that actually need a config object all re-use the same `BASE_TEST_CFG`
    config, to avoid creating a new config for each test.
    """

    @parametrize_from(PARAMS_SINGLE_ELEMENT_NO_INTERPOLATION)
    def test_single_element_no_interpolation(
        self, definition: str, expected: Any
    ) -> None:
        parse_tree, expected_visit = self._parse("singleElement", definition, expected)
        if parse_tree is None:
            return

        # Since there are no interpolations here, we do not need to provide
        # callbacks to resolve them, and the quoted string callback can simply
        # be the identity.
        visitor = grammar_visitor.GrammarVisitor(
            node_interpolation_callback=None,
            resolver_interpolation_callback=None,
            memo=None,
        )
        self._visit(lambda: visitor.visit(parse_tree), expected_visit)

    @parametrize_from(PARAMS_SINGLE_ELEMENT_WITH_INTERPOLATION)
    def test_single_element_with_resolver(
        self, restore_resolvers: Any, definition: str, expected: Any
    ) -> None:
        parse_tree, expected_visit = self._parse("singleElement", definition, expected)

        OmegaConf.register_new_resolver("test", self._resolver_test)
        OmegaConf.register_new_resolver("first", self._resolver_first)
        OmegaConf.register_new_resolver("ns1.ns2.test", self._resolver_test)

        self._visit_with_config(parse_tree, expected_visit)

    @parametrize_from(PARAMS_CONFIG_VALUE)
    def test_config_value(
        self, restore_resolvers: Any, definition: str, expected: Any
    ) -> None:
        parse_tree, expected_visit = self._parse("configValue", definition, expected)
        OmegaConf.register_new_resolver("test", self._resolver_test)
        self._visit_with_config(parse_tree, expected_visit)

    @parametrize_from(
        [
            ("trailing_comma", "${test:a,b,}", ["a", "b", ""]),
            ("empty_middle", "${test:a,,b}", ["a", "", "b"]),
            ("empty_first", "${test:,a,b}", ["", "a", "b"]),
            ("single_comma", "${test:,}", ["", ""]),
            (
                "mixed_with_ws",
                "${test:  ,a,b,\t,,c,  \t   \t ,d,, \t}",
                ["", "a", "b", "", "", "c", "", "d", "", ""],
            ),
        ]
    )
    def test_deprecated_empty_args(
        self, restore_resolvers: Any, definition: str, expected: Any
    ) -> None:
        OmegaConf.register_new_resolver("test", self._resolver_test)

        parse_tree, expected_visit = self._parse("singleElement", definition, expected)
        with warns(
            UserWarning, match=re.escape("https://github.com/omry/omegaconf/issues/572")
        ):
            self._visit_with_config(parse_tree, expected_visit)

    def _check_is_same_type(self, value: Any, expected: Any) -> None:
        """
        Helper function to validate that types of `value` and `expected are the same.

        This function assumes that `value == expected` holds, and performs a "deep"
        comparison of types (= it goes into data structures like dictionaries, lists
        and tuples).

        Note that dictionaries being compared must have keys ordered the same way!
        """
        assert type(value) is type(expected)
        if isinstance(value, (str, int, float)):
            pass
        elif isinstance(value, (list, tuple, ListConfig)):
            for vx, ex in zip(value, expected):
                self._check_is_same_type(vx, ex)
        elif isinstance(value, (dict, DictConfig)):
            for (vk, vv), (ek, ev) in zip(value.items(), expected.items()):
                assert vk == ek, "dictionaries are not ordered the same"
                self._check_is_same_type(vk, ek)
                self._check_is_same_type(vv, ev)
        elif value is None:
            assert expected is None
        else:
            raise NotImplementedError(type(value))

    def _get_expected(self, expected: Any) -> Tuple[Any, Any]:
        """Obtain the expected result of the parse & visit steps"""
        if isinstance(expected, tuple):
            # Outcomes of both the parse and visit steps are provided.
            assert len(expected) == 2
            return expected[0], expected[1]
        elif expected is GrammarParseError:
            # If only a `GrammarParseError` is expected, assume it happens in parse step.
            return expected, None
        else:
            # If anything else is provided, assume it is the outcome of the visit step.
            return None, expected

    def _get_lexer_mode(self, rule: str) -> str:
        return {"configValue": "DEFAULT_MODE", "singleElement": "VALUE_MODE"}[rule]

    def _parse(
        self, rule: str, definition: str, expected: Any
    ) -> Tuple[Optional[Antlr4ParserRuleContext], Any]:
        """
        Parse the expression given by `definition`.

        Return both the parse tree and the expected result when visiting this tree.
        """

        def get_tree() -> Antlr4ParserRuleContext:
            return grammar_parser.parse(
                value=definition,
                parser_rule=rule,
                lexer_mode=self._get_lexer_mode(rule),
            )

        expected_parse, expected_visit = self._get_expected(expected)
        if expected_parse is None:
            return get_tree(), expected_visit
        else:  # expected failure on the parse step
            with raises(expected_parse):
                get_tree()
            return None, None

    def _resolver_first(self, item: Any, *_: Any) -> Any:
        """Resolver that returns the first element of its first input"""
        try:
            return next(iter(item))
        except StopIteration:
            assert False  # not supposed to happen in current tests

    def _resolver_test(self, *args: Any) -> Any:
        """Resolver that returns the list of its inputs"""
        return args[0] if len(args) == 1 else list(args)

    def _visit(self, visit: Callable[[], Any], expected: Any) -> None:
        """Run the `visit()` function to visit the parse tree and validate the result"""
        if isinstance(expected, type) and issubclass(expected, Exception):
            with raises(expected):
                visit()
        else:
            result = visit()
            if expected is math.nan:
                # Special case since nan != nan.
                assert math.isnan(result)
            else:
                assert result == expected
                # We also check types in particular because instances of `Node` are very
                # good at mimicking their underlying type's behavior, and it is easy to
                # fail to notice that the result contains nodes when it should not.
                self._check_is_same_type(result, expected)

    def _visit_with_config(
        self, parse_tree: Antlr4ParserRuleContext, expected: Any
    ) -> None:
        """Visit the tree using the default config `BASE_TEST_CFG`"""
        if parse_tree is None:
            return
        cfg = BASE_TEST_CFG

        def visit() -> Any:
            return _utils._get_value(
                cfg.resolve_parse_tree(
                    parse_tree,
                    # Create a dummy `AnyNode` (it should not actually be used in these
                    # grammer tests, but `resolve_parse_tree()` requires it).
                    node=AnyNode(None, parent=cfg),
                    key=None,
                )
            )

        self._visit(visit, expected)


@mark.parametrize(
    "expression",
    [
        "${foo}",
        "${foo.bar}",
        "${a_b.c123}",
        "${  foo \t}",
        "x ${ab.cd.ef.gh} y",
        "$ ${foo} ${bar} ${boz} $",
        "${foo:bar}",
        "${foo-bar:bar-foo}",
        "${foo : bar, baz, boz}",
        "${foo:bar,0,a-b+c*d/$.%@?|}",
        r"\${foo}",
        "${foo.bar:boz}",
        "${$foo.bar$.x$y}",
        "${$0.1.2$}",
        "${0foo}",
        # getitem syntax
        "${foo[bar]}",
        "${foo.bar[baz]}",
        "${foo[bar].baz}",
        "${foo[bar].baz[boz]}",
        "${[foo]}",
        "${[foo].bar}",
        "${[foo][bar]}",
        # relative interpolations
        "${..foo}",
        "${..foo.bar}",
        "${..foo[bar]}",
        "${..[foo].bar}",
    ],
)
class TestMatchSimpleInterpolationPattern:
    def test_regex(self, expression: str) -> None:
        assert grammar_parser.SIMPLE_INTERPOLATION_PATTERN.match(expression) is not None

    def test_grammar_consistency(self, expression: str) -> None:
        # The expression should be valid according to the grammar.
        grammar_parser.parse(
            value=expression,
            parser_rule="configValue",
            lexer_mode="DEFAULT_MODE",
        )


@mark.parametrize(
    ("expression", "is_valid_grammar"),
    [
        # Also invalid according to the grammar.
        ("${.}", False),
        ("${..}", False),
        ("${}", False),
        ("${foo", False),
        ("${0foo:bar}", False),
        ("${foo . bar}", False),
        ("${ns . f:var}", False),
        ("${$foo:bar}", False),
        ("${.foo:bar}", False),
        (r"${foo:\}", False),
        # Valid according to the grammar but not matched by the regex.
        ("${foo.${bar}}", True),
        ("${foo:${bar}}", True),
        ("${foo:'hello'}", True),
        (r"\${foo", True),
    ],
)
class TestDoNotMatchSimpleInterpolationPattern:
    def test_regex(self, expression: str, is_valid_grammar: bool) -> None:
        assert grammar_parser.SIMPLE_INTERPOLATION_PATTERN.match(expression) is None

    def test_grammar_consistency(self, expression: str, is_valid_grammar: bool) -> None:
        ctx: Any = nullcontext() if is_valid_grammar else raises(GrammarParseError)
        with ctx:
            grammar_parser.parse(
                value=expression,
                parser_rule="configValue",
                lexer_mode="DEFAULT_MODE",
            )


def test_empty_stack() -> None:
    """
    Check that an empty stack during ANTLR parsing raises a `GrammarParseError`.
    """
    with raises(GrammarParseError):
        grammar_parser.parse("ab}", lexer_mode="VALUE_MODE")


@mark.parametrize(
    ("inter", "key", "expected"),
    [
        # config root
        # simple
        param("${dict.bar}", "", 20, id="dict_value"),
        param("${dict}", "", {"bar": 20}, id="dict_node"),
        param("${list}", "", [1, 2], id="list_node"),
        param("${list.0}", "", 1, id="list_value"),
        # relative
        param(
            "${..list}",
            "dict",
            [1, 2],
            id="relative:list_from_dict",
        ),
        param("${..list.1}", "dict", 2, id="up_down"),
        param("${..[list][1]}", "dict", 2, id="up_down_getitem"),
    ],
)
def test_parse_interpolation(inter: Any, key: Any, expected: Any) -> None:
    cfg = OmegaConf.create(
        {
            "dict": {"bar": 20},
            "list": [1, 2],
        },
    )

    root = OmegaConf.select(cfg, key)

    tree = grammar_parser.parse(
        parser_rule="singleElement",
        value=inter,
        lexer_mode="VALUE_MODE",
    )

    def callback(inter_key: Any, memo: Optional[Set[int]]) -> Any:
        assert isinstance(root, Container)
        ret = root._resolve_node_interpolation(inter_key=inter_key, memo=memo)
        return ret

    visitor = grammar_visitor.GrammarVisitor(
        node_interpolation_callback=callback,
        resolver_interpolation_callback=None,  # type: ignore
        memo=None,
    )
    ret = visitor.visit(tree)
    assert ret == expected


def test_custom_resolver_param_supported_chars() -> None:
    supported_chars = r"abc123_:" + UNQUOTED_SPECIAL
    c = OmegaConf.create({"dir1": "${copy:" + supported_chars + "}"})

    OmegaConf.register_new_resolver("copy", lambda x: x)
    assert c.dir1 == supported_chars


def test_valid_chars_in_interpolation() -> None:
    valid_chars = "".join(
        chr(i) for i in range(33, 128) if chr(i) not in INVALID_CHARS_IN_KEY_NAMES
    )
    cfg_dict = {valid_chars: 123, "inter": f"${{{valid_chars}}}"}
    cfg = OmegaConf.create(cfg_dict)
    # Test that we can access the node made of all valid characters, both
    # directly and through interpolations.
    assert cfg[valid_chars] == 123
    assert cfg.inter == 123


@mark.parametrize("c", list(INVALID_CHARS_IN_KEY_NAMES))
def test_invalid_chars_in_interpolation(c: str) -> None:
    def create() -> DictConfig:
        return OmegaConf.create({"invalid": f"${{ab{c}de}}"})

    # Test that all invalid characters trigger errors in interpolations.
    if c in [".", "}"]:
        # With '.', we try to access `${ab.de}`.
        # With '}', we try to access `${ab}`.
        cfg = create()
        with raises(InterpolationKeyError):
            cfg.invalid
    elif c == ":":
        # With ':', we try to run a resolver `${ab:de}`
        cfg = create()
        with raises(UnsupportedInterpolationType):
            cfg.invalid
    else:
        # Other invalid characters should be detected at creation time.
        with raises(GrammarParseError):
            create()


def test_grammar_cache_is_thread_safe() -> None:
    """
    This test ensures that we can parse strings across multiple threads in parallel.

    Besides ensuring that the parsing does not hang nor crash, we also verify that
    the lexer used in each thread is different.
    """
    n_threads = 10
    lexer_ids = []
    stop = threading.Event()

    def check_cache_lexer_id() -> None:
        # Parse a dummy string to make sure the grammar cache is populated
        # (this also checks that multiple threads can parse in parallel).
        grammar_parser.parse("foo")
        # Keep track of the ID of the cached lexer.
        lexer_ids.append(id(grammar_parser._grammar_cache.data[0]))
        # Wait until we are done.
        while not stop.is_set():
            time.sleep(0.1)

    # Launch threads.
    threads = []
    for i in range(n_threads):
        threads.append(threading.Thread(target=check_cache_lexer_id))
        threads[-1].start()

    # Wait until all threads have reported their lexer ID.
    while len(lexer_ids) < n_threads:
        time.sleep(0.1)

    # Terminate threads.
    stop.set()
    for thread in threads:
        thread.join()

    # Check that each thread used a unique lexer.
    assert len(set(lexer_ids)) == n_threads
