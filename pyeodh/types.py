from typing import Literal, TypedDict

from requests.structures import CaseInsensitiveDict

from pyeodh.api_mixin import ApiMixin

Headers = CaseInsensitiveDict
Params = dict[str, str | int]
RequestMethod = Literal["GET", "POST", "DELETE", "PUT"]


class Link(ApiMixin):
    @property
    def href(self):
        return self._href

    @property
    def rel(self):
        return self._rel

    @property
    def type(self):
        return self._type

    @property
    def title(self):
        return self._title

    @property
    def body(self):
        return self._body

    @property
    def method(self) -> RequestMethod:
        return self._method

    def _set_properties(self) -> None:
        self._href = self._make_str_prop(self._raw_data.get("href"))
        self._rel = self._make_str_prop(self._raw_data.get("rel"))
        self._type = self._make_str_prop(self._raw_data.get("type"))
        self._title = self._make_str_prop(self._raw_data.get("title"))
        self._body = self._make_dict_prop(self._raw_data.get("body"))
        self._method = self._make_prop(self._raw_data.get("method"), RequestMethod)


class SearchSortField(TypedDict):
    field: str
    direction: Literal["asc", "desc"]


class SearchFields(TypedDict):
    include: list[str]
    exclude: list[str]
