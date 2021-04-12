import re
from typing import Any

from pytest import mark, param, raises, warns

from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError


@mark.parametrize(
    ("cfg", "key", "expected_value", "expected_warning"),
    [
        param(
            {"a": 10, "b": "${oc.deprecated: a}"},
            "b",
            10,
            "'b' is deprecated. Change your code and config to use 'a'",
            id="value",
        ),
        param(
            {"a": 10, "b": "${oc.deprecated: a, '$OLD_KEY is deprecated'}"},
            "b",
            10,
            "b is deprecated",
            id="value-custom-message",
        ),
        param(
            {
                "a": 10,
                "b": "${oc.deprecated: a, ${warning}}",
                "warning": "$OLD_KEY is bad, $NEW_KEY is good",
            },
            "b",
            10,
            "b is bad, a is good",
            id="value-custom-message-config-variable",
        ),
        param(
            {"a": {"b": 10}, "b": "${oc.deprecated: a}"},
            "b",
            OmegaConf.create({"b": 10}),
            "'b' is deprecated. Change your code and config to use 'a'",
            id="dict",
        ),
        param(
            {"a": {"b": 10}, "b": "${oc.deprecated: a}"},
            "b.b",
            10,
            "'b' is deprecated. Change your code and config to use 'a'",
            id="dict_value",
        ),
        param(
            {"a": [0, 1], "b": "${oc.deprecated: a}"},
            "b",
            OmegaConf.create([0, 1]),
            "'b' is deprecated. Change your code and config to use 'a'",
            id="list",
        ),
        param(
            {"a": [0, 1], "b": "${oc.deprecated: a}"},
            "b[1]",
            1,
            "'b' is deprecated. Change your code and config to use 'a'",
            id="list_value",
        ),
    ],
)
def test_deprecated(
    cfg: Any, key: str, expected_value: Any, expected_warning: str
) -> None:
    cfg = OmegaConf.create(cfg)
    with warns(UserWarning, match=re.escape(expected_warning)):
        value = OmegaConf.select(cfg, key)
    assert value == expected_value
    assert type(value) == type(expected_value)


@mark.parametrize(
    ("cfg", "error"),
    [
        param(
            {"a": "${oc.deprecated: z}"},
            "ConfigKeyError raised while resolving interpolation:"
            " In oc.deprecated resolver at 'a': Key not found: 'z'",
            id="target_not_found",
        ),
        param(
            {"a": "${oc.deprecated: 111111}"},
            "TypeError raised while resolving interpolation: oc.deprecated:"
            " interpolation key type is not a string (int)",
            id="invalid_key_type",
        ),
        param(
            {"a": "${oc.deprecated: b, 1000}", "b": 10},
            "TypeError raised while resolving interpolation: oc.deprecated:"
            " interpolation message type is not a string (int)",
            id="invalid_message_type",
        ),
    ],
)
def test_deprecated_target_not_found(cfg: Any, error: str) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(
        InterpolationResolutionError,
        match=re.escape(error),
    ):
        cfg.a
