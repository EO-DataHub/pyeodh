from dataclasses import dataclass
from typing import Literal, Type, TypedDict, TypeVar

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


L = TypeVar("L", bound="Link")


@dataclass
class Link:
    rel: str
    href: str
    title: str | None = None
    media_type: str | None = None

    @classmethod
    def from_dict(cls: Type[L], data: dict[str, str]) -> L:
        return cls(
            rel=data["rel"],
            href=data["href"],
            title=data.get("title", None),
            media_type=data.get("type", None),
        )

    @staticmethod
    def get_link(links: list[L], rel: str) -> L | None:
        return next((ln for ln in links if rel == ln.rel), None)
