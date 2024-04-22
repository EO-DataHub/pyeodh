from functools import cached_property

from pyeodh import consts
from pyeodh.base_object import BaseObject
from pyeodh.pagination import PaginatedList
from pyeodh.utils import get_href_by_rel, join_url


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
        self._links = self._make_list_of_dicts_prop(self._raw_data.get("links", []))
        self._assets = self._make_dict_prop(self._raw_data.get("assets", {}))


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

    @cached_property
    def items_url(self) -> str:
        self_url = get_href_by_rel(self._links, "self")
        return join_url(self_url, "items")

    def _set_properties(self) -> None:
        self._type = self._make_str_prop(self._raw_data.get("type"))
        self._id = self._make_str_prop(self._raw_data.get("id"))
        self._title = self._make_str_prop(self._raw_data.get("title"))
        self._description = self._make_str_prop(self._raw_data.get("description"))
        self._stac_version = self._make_str_prop(self._raw_data.get("stac_version"))
        self._license = self._make_str_prop(self._raw_data.get("license"))
        self._summaries = self._make_dict_prop(self._raw_data.get("summaries", {}))
        self._extent = self._make_dict_prop(self._raw_data.get("extent", {}))
        self._links = self._make_list_of_dicts_prop(self._raw_data.get("links", []))

    def get_items(self) -> list[Item]:
        return PaginatedList(
            Item,
            self._client,
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
        self._links = self._make_list_of_dicts_prop(self._raw_data.get("links", []))

    @cached_property
    def collections_url(self) -> str:
        return get_href_by_rel(self._links, "data")

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
        url = join_url(get_href_by_rel(self._links, "self"), "conformance")
        headers, response = self._client._request_json("GET", url)
        return response.get("conformsTo", [])
