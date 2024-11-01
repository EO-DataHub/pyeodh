from unittest.mock import Mock

import pytest

from pyeodh.eodh_object import EodhObject
from pyeodh.pagination import PaginatedList


class DummyItem(EodhObject):
    """A simple test object class inheriting from EodhObject."""

    def __init__(self, client, headers, data, parent=None):
        super().__init__(client, headers, data, parent)

    def _set_props(self, obj: dict) -> None:
        self.id = obj.get("id")


@pytest.fixture
def mock_client():
    """Fixture to create a mock client."""
    return Mock()


@pytest.fixture
def paginated_list(mock_client):
    """Fixture to create a PaginatedList instance."""
    return PaginatedList(
        DummyItem,
        mock_client,
        "GET",
        "https://api.example.com/items",
        "items",
        params={"param1": "value1"},
    )


def test_get_limited_first_page(paginated_list, mock_client):
    """Test get_limited() when fetching the first page of results."""
    mock_response = {
        "items": [{"id": i} for i in range(10)],
        "links": [{"rel": "next", "href": "https://api.example.com/items?page=2"}],
        "context": {"matched": 25},
    }
    mock_client._request_json.return_value = ({}, mock_response)

    result = paginated_list.get_limited()

    assert len(result) == 10
    assert all(isinstance(item, DummyItem) for item in result)
    assert [item.id for item in result] == list(range(10))


def test_get_limited_partial_page(paginated_list, mock_client):
    """Test get_limited() when fetching a partial page of results."""
    mock_response = {
        "items": [{"id": i} for i in range(5)],
        "links": [],
        "context": {"matched": 5},
    }
    mock_client._request_json.return_value = ({}, mock_response)

    result = paginated_list.get_limited()

    assert len(result) == 5
    assert all(isinstance(item, DummyItem) for item in result)
    assert [item.id for item in result] == list(range(5))


def test_get_limited_custom_limit(mock_client):
    """Test get_limited() with a custom pagination limit."""
    custom_limit = 15
    paginated_list = PaginatedList(
        DummyItem,
        mock_client,
        "GET",
        "https://api.example.com/items",
        "items",
        params={"param1": "value1"},
        first_data={"per_page": custom_limit},
    )

    mock_response = {
        "items": [{"id": i} for i in range(custom_limit)],
        "links": [{"rel": "next", "href": "https://api.example.com/items?page=2"}],
        "context": {"matched": 30},
    }
    mock_client._request_json.return_value = ({}, mock_response)

    result = paginated_list.get_limited()

    assert len(result) == custom_limit
    assert all(isinstance(item, DummyItem) for item in result)
    assert [item.id for item in result] == list(range(custom_limit))


def test_get_limited_cached_results(paginated_list, mock_client):
    """Test get_limited() when results are already cached."""
    # Populate the _elements list
    paginated_list._elements = [
        DummyItem(mock_client, {}, {"id": i}) for i in range(10)
    ]

    result = paginated_list.get_limited()

    assert len(result) == 10
    assert all(isinstance(item, DummyItem) for item in result)
    assert [item.id for item in result] == list(range(10))
    mock_client._request_json.assert_not_called()


def test_iter_method(mock_client):
    """Test the __iter__ method of PaginatedList."""
    paginated_list = PaginatedList(
        DummyItem,
        mock_client,
        "GET",
        "https://api.example.com/items",
        "items",
        params={"param1": "value1"},
    )

    # Mock responses for multiple pages
    mock_responses = [
        {
            "items": [{"id": i} for i in range(5)],
            "links": [{"rel": "next", "href": "https://api.example.com/items?page=2"}],
            "context": {"matched": 15},
        },
        {
            "items": [{"id": i} for i in range(5, 10)],
            "links": [{"rel": "next", "href": "https://api.example.com/items?page=3"}],
            "context": {"matched": 15},
        },
        {
            "items": [{"id": i} for i in range(10, 15)],
            "links": [],
            "context": {"matched": 15},
        },
    ]

    mock_client._request_json.side_effect = [
        ({}, response) for response in mock_responses
    ]

    # Use the iterator to fetch all items
    items = list(paginated_list)

    assert len(items) == 15
    assert all(isinstance(item, DummyItem) for item in items)
    assert [item.id for item in items] == list(range(15))

    # Check that _request_json was called for each page
    assert mock_client._request_json.call_count == 3


def test_iter_method_empty_response(mock_client):
    """Test the __iter__ method of PaginatedList with an empty response."""
    paginated_list = PaginatedList(
        DummyItem,
        mock_client,
        "GET",
        "https://api.example.com/items",
        "items",
        params={"param1": "value1"},
    )

    mock_response = {
        "items": [],
        "links": [],
        "context": {"matched": 0},
    }

    mock_client._request_json.return_value = ({}, mock_response)

    items = list(paginated_list)

    assert len(items) == 0
    mock_client._request_json.assert_called_once()


def test_iter_method_single_page(mock_client):
    """Test the __iter__ method of PaginatedList with a single page response."""
    paginated_list = PaginatedList(
        DummyItem,
        mock_client,
        "GET",
        "https://api.example.com/items",
        "items",
        params={"param1": "value1"},
    )

    mock_response = {
        "items": [{"id": i} for i in range(5)],
        "links": [],
        "context": {"matched": 5},
    }

    mock_client._request_json.return_value = ({}, mock_response)

    items = list(paginated_list)

    assert len(items) == 5
    assert all(isinstance(item, DummyItem) for item in items)
    assert [item.id for item in items] == list(range(5))
    mock_client._request_json.assert_called_once()


def test_fetch_next_raises_runtime_error(mock_client):
    paginated_list = PaginatedList(
        DummyItem,
        mock_client,
        "GET",
        "https://api.example.com/items",
        "items",
        params={"param1": "value1"},
    )

    # Set _next_url to None to simulate missing next URL
    paginated_list._next_url = None

    with pytest.raises(RuntimeError, match="Next url not specified!"):
        paginated_list._fetch_next()

    mock_client._request_json.assert_not_called()
