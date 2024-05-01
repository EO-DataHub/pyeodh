from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Iterator, Type, TypeVar

from pyeodh.base_object import BaseObject
from pyeodh.types import Headers, Params, RequestMethod

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client

T = TypeVar("T", bound=BaseObject)


class PaginatedList(Generic[T]):

    def __init__(
        self,
        cls: Type[T],
        client: Client,
        method: RequestMethod,
        first_url: str,
        list_key: str,
        headers: Headers | None = None,
        params: Params | None = None,
        first_data: dict | None = None,
    ) -> None:
        self._elements: list[T] = []
        self._cls = cls
        self._client = client
        self._method: RequestMethod = method
        self._next_url: str | None = first_url
        self._headers = headers
        self._params = params
        self._total_count: int | None = None
        self._list_key = list_key
        self._data = first_data

    @property
    def total_count(self):
        return self._total_count

    def __iter__(self) -> Iterator[T]:
        yield from self._elements
        while self._has_next():
            new_elements = self._fetch_next()
            self._elements += new_elements
            yield from new_elements

    def _has_next(self) -> bool:
        return self._next_url is not None

    def _fetch_next(self) -> list[T]:
        if not self._next_url:
            raise RuntimeError("Next url not specified!")
        headers, resp_data = self._client._request_json(
            self._method,
            self._next_url,
            headers=self._headers,
            params=self._params,
            data=self._data,
        )
        next_link = next(
            filter(lambda ln: ln.get("rel") == "next", resp_data.get("links", {})), {}
        )
        self._next_url = next_link.get("href")

        # NOTE: temp fix for broken next links given by the API
        if self._has_next():
            self._next_url = self._next_url.replace(
                "org.uk/collections", "org.uk/stac-fastapi/collections"
            )
            self._next_url = self._next_url.replace(
                "org.uk/search", "org.uk/stac-fastapi/search"
            )

        self._data = next_link.get("body")
        self._total_count = resp_data.get("context", {}).get("matched")
        if not resp_data:
            return []
        if self._list_key in resp_data:
            resp_data = resp_data[self._list_key]

        return [
            self._cls(
                self._client,
                headers,
                element,
            )
            for element in resp_data
            if element is not None
        ]
