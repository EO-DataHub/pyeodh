from functools import cached_property

from pyeodh import consts
from pyeodh.base_object import BaseObject
from pyeodh.pagination import PaginatedList
from pyeodh.utils import get_href_by_rel, join_url


class Item(BaseObject):

    @property
    def id(self) -> str:
        return self._id

    def _set_properties(self) -> None:
        self._id = self._raw_data.get("id")


class Collection(BaseObject):

    @property
    def links(self) -> list[dict]:
        return self._links

    @cached_property
    def items_url(self) -> str:
        self_url = get_href_by_rel(self._links, "self")
        return join_url(self_url, "items")

    @property
    def description(self) -> str:
        return self._description

    def _set_properties(self) -> None:
        self._links = self._raw_data.get("links")
        self._description = self._raw_data.get("description")

    def get_items(self) -> list[Item]:
        return PaginatedList(
            Item,
            self._client,
            self.items_url,
            "features",
            params={"limit": consts.PAGINATION_LIMIT},
        )


class ResourceCatalog(BaseObject):

    @property
    def links(self) -> list[dict]:
        return self._links

    @cached_property
    def collections_url(self) -> str:
        return get_href_by_rel(self._links, "data")

    def _set_properties(self) -> None:
        self._links = self._raw_data.get("links")

    def get_collections(self) -> list[Collection]:
        """Fetches all resource catalog collections.

        Returns:
            list[Collection]: List of available collections
        """

        headers, response = self._client._request_json("GET", self.collections_url)
        collections = []

        for item in response.get("collections"):
            collections.append(Collection(self._client, headers, item))

        return collections

    def get_collection(self, name: str) -> Collection:
        """Fetches a resource catalog collection.

        Args:
            name (str): ID of a collection

        Returns:
            Collection: Collection for given ID
        """
        url = join_url(self.collections_url, name)
        headers, response = self._client._request_json("GET", url)

        return Collection(self._client, headers, response)
