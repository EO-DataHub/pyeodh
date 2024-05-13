from __future__ import annotations

from functools import cached_property
from typing import Any, Literal, Type, TypeVar, TYPE_CHECKING

from pystac import Collection, Extent, Item, Summaries
from pystac.asset import Asset
from pystac.provider import Provider

from pyeodh import consts
from pyeodh.api_mixin import ApiMixin, is_optional
from pyeodh.client import Client
from pyeodh.pagination import PaginatedList
from pyeodh.types import Headers, Link, SearchFields, SearchSortField
from pyeodh.utils import get_link_by_rel, join_url, remove_null_items

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from datetime import datetime as Datetime

C = TypeVar("C", bound="EodhCollection")


class EodhItem(Item, ApiMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_dict(
        cls: Type[C], client: Client, headers: Headers, raw_data: dict[str, Any]
    ) -> C:
        item = super().from_dict(raw_data)
        ApiMixin.__init__(item, client=client, headers=headers, data=raw_data)
        return item

    def _update_properties(self, obj: Item) -> None:
        self.__dict__.update(obj.__dict__)

    @cached_property
    def self_url(self) -> str:
        self_link = get_link_by_rel(self.links, "self")
        if not self_link:
            # NOTE: workaround for api not returning links for item creation
            return join_url(
                consts.API_BASE_URL,
                "stac-fastapi/collections",
                self.collection or "",
                "items",
                self.id or "",
            )
        if not self_link.href:
            raise RuntimeError("Object does not contain URL pointing to self.")
        return self_link.href

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self.self_url)

    def update(
        self,
        geometry: dict[str, Any] | None = None,
        bbox: list[float] | None = None,
        datetime: Datetime | None = None,
        properties: dict[str, Any] | None = None,
        collection: str | Collection | None = None,
        assets: dict[str, Any] | None = None,
    ) -> None:

        put_data = remove_null_items(
            {
                "id": self.id,
                "geometry": geometry or self.geometry,  # NOTE: getting 500 with this
                "bbox": bbox or self.bbox,
                "datetime": datetime or self.datetime,
                "properties": properties or self.properties,
                "collection": collection or self.collection,
                "assets": assets or self.assets,
            }
        )

        _, resp_data = self._client._request_json("PUT", self.self_url, data=put_data)

        if resp_data:
            self._update_properties(
                self.from_dict(self._client, self._headers, resp_data)
            )


class EodhCollection(Collection, ApiMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_dict(
        cls: Type[C], client: Client, headers: Headers, raw_data: dict[str, Any]
    ) -> C:
        col = super().from_dict(raw_data)
        ApiMixin.__init__(col, client=client, headers=headers, data=raw_data)
        return col

    def _update_properties(self, obj: Collection) -> None:
        self.__dict__.update(obj.__dict__)

    @cached_property
    def items_url(self) -> str:
        return join_url(self.self_url, "items")

    @cached_property
    def self_url(self) -> str:
        self_link = get_link_by_rel(self.links, "self")
        if not self_link or not self_link.href:
            raise RuntimeError("Object does not contain URL pointing to self.")
        return self_link.href

    def get_items(self) -> PaginatedList[EodhItem]:
        return PaginatedList(
            EodhItem,
            self._client,
            "GET",
            self.items_url,
            "features",
            params={"limit": consts.PAGINATION_LIMIT},
        )

    def get_item(self, item_id: str) -> EodhItem:
        """Fetches a collection item.
        Calls: GET /collections/{collection_id}/items/{item_id}

        Args:
            item_id (str): ID of a collection item

        Returns:
            Item: Item for given ID
        """
        url = join_url(self.items_url, item_id)
        headers, response = self._client._request_json("GET", url)

        return EodhItem.from_dict(self._client, headers, response)

    def update(
        self,
        description: str | None = None,
        extent: Extent | None = None,
        title: str | None = None,
        license: str | None = None,
        keywords: list[str] | None = None,
        providers: list[Provider] | None = None,
        summaries: Summaries | None = None,
        assets: dict[str, Asset] | None = None,
    ) -> None:
        assert is_optional(description, str), description
        assert is_optional(extent, Extent), extent
        assert is_optional(title, str), title
        assert is_optional(license, str), license
        assert is_optional(keywords, list), keywords
        assert is_optional(providers, list), providers
        assert is_optional(summaries, Summaries), summaries
        assert is_optional(assets, dict), assets

        put_data = remove_null_items(
            {
                "id": self.id,
                "description": description or self.description,
                "extent": extent or self.extent,
                "title": title or self.title,
                "license": license or self.license,
                "keywords": keywords or self.keywords,
                "providers": providers or self.providers,
                "summaries": summaries or self.summaries,
                "assets": assets or self.assets,
            }
        )

        # _, resp_data = self._client._request_json("PUT", self.self_url, data=put_data)
        # NOTE: temp workaround until test is fixed
        _, resp_data = self._client._request_json(
            "PUT",
            "https://test.eodatahub.org.uk/stac-fastapi/collections",
            data=put_data,
        )
        if resp_data:
            self._update_properties(
                self.from_dict(self._client, self._headers, resp_data)
            )

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self.self_url)

    def create_item(
        self,
        id: str,
        geometry: dict[str, Any] | None,
        bbox: list[float] | None,
        datetime: Datetime | None,
        properties: dict[str, Any] | None,
        collection: str | Collection | None = None,
        assets: dict[str, Any] | None = None,
    ) -> EodhItem:

        post_data = remove_null_items(
            {
                "id": self.id,
                "geometry": geometry,
                "bbox": bbox,
                "datetime": datetime,
                "properties": properties,
                "collection": collection,
                "assets": assets,
            }
        )

        headers, response = self._client._request_json(
            "POST", self.items_url, data=post_data
        )
        return EodhItem.from_dict(self._client, headers, response)


class ResourceCatalog(ApiMixin):

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
        assert isinstance(self._raw_data, dict)
        self._type = self._make_str_prop(self._raw_data.get("type"))
        self._id = self._make_str_prop(self._raw_data.get("id"))
        self._title = self._make_str_prop(self._raw_data.get("title"))
        self._description = self._make_str_prop(self._raw_data.get("description"))
        self._stac_version = self._make_str_prop(self._raw_data.get("stac_version"))
        self._conforms_to = self._make_list_of_strs_prop(
            self._raw_data.get("conformsTo", [])
        )
        self._links = self._make_list_of_classes_prop(
            Link, self._raw_data.get("links", [])
        )

    @cached_property
    def self_url(self) -> str:
        self_link = get_link_by_rel(self.links, "self")
        if not self_link or not self_link.href:
            raise RuntimeError("Object does not contain URL pointing to self.")
        return self_link.href

    @cached_property
    def collections_url(self) -> str:
        data_link = get_link_by_rel(self.links, "data")
        if not data_link or not data_link.href:
            raise RuntimeError("Object does not contain URL pointing to collections.")
        return data_link.href

    def get_collections(self) -> list[EodhCollection]:
        """Fetches all resource catalog collections.
        Calls: GET /collections

        Returns:
            list[Collection]: List of available collections
        """

        headers, response = self._client._request_json("GET", self.collections_url)
        if not response:
            return []
        return [
            EodhCollection.from_dict(self._client, headers, item)
            for item in response.get("collections", [])
        ]

    def get_collection(self, collection_id: str) -> EodhCollection:
        """Fetches a resource catalog collection.
        Calls: GET /collections/{collection_id}

        Args:
            collection_id (str): ID of a collection

        Returns:
            Collection: Collection for given ID
        """
        url = join_url(self.collections_url, collection_id)
        headers, response = self._client._request_json("GET", url)

        return EodhCollection.from_dict(self._client, headers, response)

    def get_conformance(self) -> list[str]:
        url = join_url(self.self_url, "conformance")
        _, response = self._client._request_json("GET", url)
        return response.get("conformsTo", [])

    def search(
        self,
        limit: int = consts.PAGINATION_LIMIT,
        collections: list[str] | None = None,
        ids: list[str] | None = None,
        bbox: list[Any] | None = None,
        intersects: dict | None = None,
        datetime: str | None = None,
        fields: SearchFields | None = None,
        query: dict | None = None,
        sort_by: list[SearchSortField] | None = None,
        filter: dict | None = None,
        filter_crs: str | None = None,
        filter_lang: Literal["cql-json", "cql2-json", "cql2-text"] | None = None,
    ) -> PaginatedList[Item]:
        assert isinstance(limit, int), limit
        assert is_optional(collections, list), collections
        assert is_optional(ids, list), ids
        assert is_optional(bbox, list), bbox
        assert is_optional(intersects, dict), intersects
        assert is_optional(datetime, str), datetime
        assert is_optional(fields, dict), fields
        assert is_optional(query, dict), query
        assert is_optional(sort_by, list), sort_by
        assert is_optional(filter, dict), filter
        assert is_optional(filter_crs, str), filter_crs
        assert filter_lang in ["cql-json", "cql2-json", "cql2-text", None]

        data = remove_null_items(
            {
                "limit": limit,
                "collections": collections,
                "ids": ids,
                "bbox": bbox,
                "intersects": intersects,
                "datetime": datetime,
                "fields": fields,
                "query": query,
                "sortby": sort_by,
                "filter": filter,
                "filter_crs": filter_crs,
                "filter_lang": filter_lang,
            }
        )
        url = join_url(self.self_url, "search")
        return PaginatedList(
            Item, self._client, "POST", url, "features", first_data=data
        )

    def create_collection(
        self,
        id: str,
        description: str,
        extent: Extent,
        title: str | None = None,
        license: str | None = None,
        keywords: list[str] | None = None,
        providers: list[Provider] | None = None,
        summaries: Summaries | None = None,
        assets: dict[str, Asset] | None = None,
    ) -> EodhCollection:
        assert isinstance(id, str), id
        assert isinstance(description, str), description
        assert isinstance(extent, Extent), extent
        assert is_optional(title, str), title
        assert is_optional(license, str), license
        assert is_optional(keywords, list), keywords
        assert is_optional(providers, list), providers
        assert is_optional(summaries, Summaries), summaries
        assert is_optional(assets, dict), assets

        post_data = remove_null_items(
            {
                "id": id,
                "description": description,
                "extent": extent,
                "title": title,
                "license": license,
                "keywords": keywords,
                "providers": providers,
                "summaries": summaries,
                "assets": assets,
            }
        )
        headers, response = self._client._request_json(
            "POST", self.collections_url, data=post_data
        )
        return EodhCollection.from_dict(self._client, headers, response)

    def ping(self) -> str | None:
        headers, response = self._client._request_json(
            "GET", join_url(self.self_url, "_mgmt/ping")
        )
        return response.get("message")
