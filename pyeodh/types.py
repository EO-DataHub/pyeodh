from dataclasses import dataclass
from typing import Literal, Optional, Type, TypedDict, TypeVar, Union

from requests.structures import CaseInsensitiveDict

Headers = CaseInsensitiveDict
Params = dict[str, Union[str, int]]
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
    """A class representing a hypermedia link.

    Attributes:
        rel: The relationship type of the link.
        href: The URL the link points to.
        title: Optional title of the link.
        media_type: Optional media type of the linked resource.
    """

    rel: str
    href: str
    title: Optional[str] = None
    media_type: Optional[str] = None

    @classmethod
    def from_dict(cls: Type[L], data: dict[str, str]) -> L:
        """Create a Link instance from a dictionary.

        Args:
            data: Dictionary containing link data.

        Returns:
            A new Link instance.
        """
        return cls(
            rel=data["rel"],
            href=data["href"],
            title=data.get("title", None),
            media_type=data.get("type", None),
        )

    @staticmethod
    def get_link(links: list[L], rel: str) -> Optional[L]:
        """Find a link with the specified relationship type.

        Args:
            links: List of Link objects to search through.
            rel: The relationship type to look for.

        Returns:
            The matching Link object or None if not found.
        """
        return next((ln for ln in links if rel == ln.rel), None)
