from typing import Any
import pytest
from pyeodh.utils import is_absolute_url, join_url, remove_null_items


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://example.com", True),
        ("http://example.com", True),
        ("example.com", False),
        ("/path/to/resource", False),
        ("path/to/resource", False),
        ("", False),
    ],
)
def test_is_absolute_url(url: str, expected: bool) -> None:
    assert is_absolute_url(url) == expected


@pytest.mark.parametrize(
    "args, expected",
    [
        (
            ("https://example.com", "path", "to", "resource"),
            "https://example.com/path/to/resource",
        ),
        (
            ("https://example.com/", "path", "to", "resource"),
            "https://example.com/path/to/resource",
        ),
        (("https://example.com", "/path", "to", "resource"), ValueError),
        (
            ("https://example.com", "path/with/slash/", "resource"),
            "https://example.com/path/with/slash/resource",
        ),
        (("", "path", "to", "resource"), "path/to/resource"),
        (("/path", "to", "resource"), "/path/to/resource"),
    ],
)
def test_join_url(args: tuple[str, ...], expected: str | type[ValueError]) -> None:
    if expected is ValueError:
        with pytest.raises(ValueError):
            join_url(*args)
    else:
        assert join_url(*args) == expected


@pytest.mark.parametrize(
    "input_dict, expected_dict",
    [
        ({"a": 1, "b": None, "c": 3}, {"a": 1, "c": 3}),
        ({"a": None, "b": None, "c": None}, {}),
        ({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 2, "c": 3}),
        ({"a": 0, "b": "", "c": False, "d": None}, {"a": 0, "b": "", "c": False}),
        ({}, {}),
    ],
)
def test_remove_null_items(
    input_dict: dict[str, Any], expected_dict: dict[str, Any]
) -> None:
    assert remove_null_items(input_dict) == expected_dict
