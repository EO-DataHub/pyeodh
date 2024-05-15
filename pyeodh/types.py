from typing import Literal, TypedDict

from requests.structures import CaseInsensitiveDict

Headers = CaseInsensitiveDict
Params = dict[str, str | int]
RequestMethod = Literal["GET", "POST", "DELETE", "PUT"]


class SearchSortField(TypedDict):
    field: str
    direction: Literal["asc", "desc"]


class SearchFields(TypedDict):
    include: list[str]
    exclude: list[str]
