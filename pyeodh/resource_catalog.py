from functools import cached_property
from typing import Any

from pyeodh import consts
from pyeodh.base_object import BaseObject, is_optional
from pyeodh.pagination import PaginatedList
from pyeodh.types import Link
from pyeodh.utils import get_link_by_rel, join_url, remove_null_items


class Item(BaseObject):

    @property
    def type(self):
        return self._type

    @property
    def stac_version(self):
        return self._stac_version

    @property
    def id(self):
        return self._id

    @property
    def collection(self):
        return self._collection

    @property
    def geometry(self):
        return self._geometry

    @property
    def bbox(self):
        return self._bbox

    @property
    def properties(self):
        return self._properties

    @property
    def links(self):
        return self._links

    @property
    def assets(self):
        return self._assets

    def _set_properties(self) -> None:
        self._type = self._make_str_prop(self._raw_data.get("type"))
        self._stac_version = self._make_str_prop(self._raw_data.get("stac_version"))
        self._id = self._make_str_prop(self._raw_data.get("id"))
        self._collection = self._make_str_prop(self._raw_data.get("collection"))
        self._geometry = self._make_dict_prop(self._raw_data.get("geometry", {}))
        self._bbox = self._make_list_of_floats_prop(self._raw_data.get("bbox", []))
        self._properties = self._make_dict_prop(self._raw_data.get("properties", {}))
        self._links = self._make_list_of_classes_prop(Link, self._raw_data.get("links"))
        self._assets = self._make_dict_prop(self._raw_data.get("assets", {}))

    @cached_property
    def self_url(self) -> str:
        return get_link_by_rel(self.links, "self").href

    def delete(self) -> None:
        self._client._request_json("DELETE", self.self_url)


class Collection(BaseObject):
    @property
    def type(self):
        return self._type

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def stac_version(self):
        return self._stac_version

    @property
    def license(self):
        return self._license

    @property
    def summaries(self):
        return self._summaries

    @property
    def extent(self):
        return self._extent

    @property
    def links(self):
        return self._links

    def _set_properties(self) -> None:
        self._type = self._make_str_prop(self._raw_data.get("type"))
        self._id = self._make_str_prop(self._raw_data.get("id"))
        self._title = self._make_str_prop(self._raw_data.get("title"))
        self._description = self._make_str_prop(self._raw_data.get("description"))
        self._stac_version = self._make_str_prop(self._raw_data.get("stac_version"))
        self._license = self._make_str_prop(self._raw_data.get("license"))
        self._summaries = self._make_dict_prop(self._raw_data.get("summaries", {}))
        self._extent = self._make_dict_prop(self._raw_data.get("extent", {}))
        self._links = self._make_list_of_classes_prop(Link, self._raw_data.get("links"))

    @cached_property
    def items_url(self) -> str:
        return join_url(self.self_url, "items")

    @cached_property
    def self_url(self) -> str:
        return get_link_by_rel(self.links, "self").href

    def get_items(self) -> PaginatedList[Item]:
        return PaginatedList(
            Item,
            self._client,
            "GET",
            self.items_url,
            "features",
            params={"limit": consts.PAGINATION_LIMIT},
        )

    def get_item(self, item_id: str) -> Item:
        """Fetches a collection item.
        Calls: GET /collections/{collection_id}/items/{item_id}

        Args:
            item_id (str): ID of a collection item

        Returns:
            Item: Item for given ID
        """
        url = join_url(self.items_url, item_id)
        headers, response = self._client._request_json("GET", url)

        return Item(self._client, headers, response)

    def delete(self) -> None:
        self._client._request_json("DELETE", self.self_url)


class ResourceCatalog(BaseObject):

    @property
    def type(self):
        return self._type

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def stac_version(self):
        return self._stac_version

    @property
    def conforms_to(self):
        return self._conforms_to

    @property
    def links(self):
        return self._links

    def _set_properties(self) -> None:
        self._type = self._make_str_prop(self._raw_data.get("type"))
        self._id = self._make_str_prop(self._raw_data.get("id"))
        self._title = self._make_str_prop(self._raw_data.get("title"))
        self._description = self._make_str_prop(self._raw_data.get("description"))
        self._stac_version = self._make_str_prop(self._raw_data.get("stac_version"))
        self._conforms_to = self._make_list_of_strs_prop(
            self._raw_data.get("conformsTo", [])
        )
        self._links = self._make_list_of_classes_prop(Link, self._raw_data.get("links"))

    @cached_property
    def self_url(self) -> str:
        return get_link_by_rel(self.links, "self").href

    @cached_property
    def collections_url(self) -> str:
        return get_link_by_rel(self.links, "data").href

    def get_collections(self) -> list[Collection]:
        """Fetches all resource catalog collections.
        Calls: GET /collections

        Returns:
            list[Collection]: List of available collections
        """

        headers, response = self._client._request_json("GET", self.collections_url)
        return [
            Collection(self._client, headers, item)
            for item in response.get("collections")
        ]

    def get_collection(self, collection_id: str) -> Collection:
        """Fetches a resource catalog collection.
        Calls: GET /collections/{collection_id}

        Args:
            collection_id (str): ID of a collection

        Returns:
            Collection: Collection for given ID
        """
        url = join_url(self.collections_url, collection_id)
        headers, response = self._client._request_json("GET", url)

        return Collection(self._client, headers, response)

    def get_conformance(self) -> list[str]:
        url = join_url(self.self_url, "conformance")
        _, response = self._client._request_json("GET", url)
        return response.get("conformsTo", [])

    def search(self, limit: int = consts.PAGINATION_LIMIT) -> PaginatedList[Item]:
        data = {"limit": limit}  # TODO build request body
        url = join_url(self.self_url, "search")
        return PaginatedList(
            Item, self._client, "POST", url, "features", first_data=data
        )

    def create_collection(
        self,
        id: str,
        title: str | None = None,
        description: str | None = None,
        stac_version: str | None = None,
        license: str | None = None,
        summaries: dict[str, Any] | None = None,
        extent: dict[str, Any] | None = None,
    ) -> Collection:
        assert isinstance(id, str), id
        assert is_optional(title, str), title
        assert is_optional(description, str), description
        assert is_optional(stac_version, str), stac_version
        assert is_optional(license, str), license
        assert is_optional(summaries, dict), summaries
        assert is_optional(extent, dict), extent

        data = remove_null_items(
            {
                "id": id,
                "title": title,
                "description": description,
                "stac_version": stac_version,
                "license": license,
                "summaries": summaries,
                "extent": extent,
            }
        )

        headers, response = self._client._request_json(
            "POST", self.collections_url, data=data
        )
        return Collection(self._client, headers, response)
