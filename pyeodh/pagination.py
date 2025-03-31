from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generic, Iterator, Type, TypeVar

from pyeodh import consts
from pyeodh.eodh_object import EodhObject
from pyeodh.types import Headers, Params, RequestMethod

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client

T = TypeVar("T", bound=EodhObject)

logger = logging.getLogger(__name__)


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
        parent: EodhObject | None = None,
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
        self._parent = parent

    @property
    def total_count(self):
        if not self._total_count:
            data: dict | None = self._data.copy() if self._data is not None else None
            params: Params | None = (
                self._params.copy() if self._params is not None else None
            )
            if data and "limit" in data:
                data["limit"] = 1
            else:
                if params is None:
                    params = {}
                params["limit"] = 1
            if not self._next_url:
                raise RuntimeError("Next url not specified!")
            _, resp_data = self._client._request_json(
                self._method,
                self._next_url,
                headers=self._headers,
                params=params,
                data=data,
            )
            self._total_count = resp_data.get("numMatched")
            if self._total_count is None:
                logger.warning("`numMatched` number is not in the response.")

        return self._total_count

    def __iter__(self) -> Iterator[T]:
        yield from self._elements
        while self._has_next():
            new_elements = self._fetch_next()
            self._elements += new_elements
            yield from new_elements

    def __getitem__(self, index: int | slice) -> Any:
        assert isinstance(index, (int, slice))
        if isinstance(index, int):
            self._fetch_to_index(index)
            return self._elements[index]
        elif isinstance(index, slice):
            return self.PagedSlice(self, index)

    def _fetch_to_index(self, index: int) -> None:
        while len(self._elements) <= index and self._has_next():
            new_elements = self._fetch_next()
            self._elements += new_elements

    def _has_next(self) -> bool:
        return self._next_url is not None

    def _fetch_next(self) -> list[T]:
        if not self._next_url:
            raise RuntimeError("Next url not specified!")
        if "/planet/search?next=" in self._next_url:
            self._next_url, next_token = self._next_url.split("?next=")
            if self._data is None:
                self._data = {}
            self._data["next"] = next_token
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
                parent=self._parent,
            )
            for element in resp_data
            if element is not None
        ]

    def get_limited(self) -> list[T]:
        """Returns the first page of the results, up to pagination limit

        Returns:
            list[T]: List of objects
        """

        limit = consts.PAGINATION_LIMIT
        if self._data:
            limit: int = self._data.get("per_page", limit)

        if len(self._elements) < limit:
            self._fetch_to_index(limit)
        return self._elements[:limit]

    class PagedSlice:
        def __init__(self, _list: PaginatedList[T], _slice: slice):
            self._list = _list
            self._start = _slice.start or 0
            self._stop = _slice.stop
            self._step = _slice.step or 1

        def __iter__(self) -> Iterator[T]:
            index = self._start
            while not (self._stop is not None and index >= self._stop):
                if len(self._list._elements) > index or self._list._has_next():
                    yield self._list[index]
                    index += self._step
                else:
                    return

        def __getitem__(self, index: int | slice) -> T:
            return self._list[index]
