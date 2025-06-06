from typing import Any, Type, Union

import pytest

from pyeodh.eodh_object import is_optional
from pyeodh.utils import is_absolute_url, join_url, remove_null_items, s3_url


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
def test_join_url(
    args: tuple[str, ...], expected: Union[str, type[ValueError]]
) -> None:
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


@pytest.mark.parametrize(
    "workspace_name, environment, path_to_file, expected",
    [
        # Basic case with staging environment
        (
            "test-workspace",
            "staging",
            "data/file.txt",
            "https://test-workspace.staging.eodatahub-workspaces.org.uk/files/"
            "workspaces-eodhp-staging/data/file.txt",
        ),
        # Path with leading slash
        (
            "test-workspace",
            "staging",
            "/data/file.txt",
            "https://test-workspace.staging.eodatahub-workspaces.org.uk/files/"
            "workspaces-eodhp-staging/data/file.txt",
        ),
        # Path with multiple leading slashes
        (
            "test-workspace",
            "staging",
            "///data/file.txt",
            "https://test-workspace.staging.eodatahub-workspaces.org.uk/files/"
            "workspaces-eodhp-staging/data/file.txt",
        ),
        # Test with test environment
        (
            "test-workspace",
            "test",
            "data/file.txt",
            "https://test-workspace.test.eodatahub-workspaces.org.uk/files/"
            "workspaces-eodhp-test/data/file.txt",
        ),
    ],
)
def test_s3_url(
    workspace_name: str, environment: str, path_to_file: str, expected: str
) -> None:
    """Test s3_url function with various input combinations.

    Args:
        workspace_name: Name of the workspace to test
        path_to_file: Path to file within workspace to test
        expected: Expected S3 URL output
    """
    result = s3_url(workspace_name, environment, path_to_file)
    assert result == expected


@pytest.mark.parametrize(
    "value, type_, expected",
    [
        # Test with single type
        (None, str, True),
        ("hello", str, True),
        (123, str, False),
        # Test with tuple of types
        (None, (str, int), True),
        ("hello", (str, int), True),
        (123, (str, int), True),
        (1.23, (str, int), False),
        # Test with various Python types
        (None, dict, True),
        ({}, dict, True),
        ([], dict, False),
        # Test with complex types
        (None, list, True),
        ([], list, True),
        ({}, list, False),
    ],
)
def test_is_optional(
    value: Any, type_: Union[Type, tuple[Type, ...]], expected: bool
) -> None:
    """Test is_optional function with various input combinations.

    Args:
        value: The value to test
        type_: The type or tuple of types to check against
        expected: Expected boolean result

    The function tests if a value is either None or matches the specified type(s).
    """
    assert is_optional(value, type_) == expected
