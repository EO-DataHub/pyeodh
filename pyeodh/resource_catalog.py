from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal, TypeVar

import pystac
import pystac.catalog
from pystac import Extent, RelType, STACObject, Summaries
from pystac.asset import Asset
from pystac.provider import Provider

from pyeodh import consts
from pyeodh.eodh_object import EodhObject, is_optional
from pyeodh.pagination import PaginatedList
from pyeodh.types import Headers, SearchFields, SearchSortField
from pyeodh.utils import join_url, remove_null_items

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from datetime import datetime as Datetime

    from pyeodh.client import Client

C = TypeVar("C", bound="STACObject")


class Item(EodhObject):
    _pystac_object: pystac.Item

    def __init__(self, client: Client, headers: Headers, data: Any):
        super().__init__(client, headers, data, pystac.Item)

    def _set_props(self, obj: pystac.Item) -> None:
        self.id = obj.id
        self.geometry = obj.geometry
        self.bbox = obj.bbox
        self.datetime = obj.datetime
        self.properties = obj.properties
        self.collection = obj.collection_id
        self.assets = obj.assets

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self._pystac_object.self_href)

    def update(
        self,
        geometry: dict[str, Any] | None = None,
        bbox: list[float] | None = None,
        datetime: Datetime | None = None,
        properties: dict[str, Any] | None = None,
        collection: str | pystac.Collection | None = None,
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

        _, resp_data = self._client._request_json(
            "PUT", self._pystac_object.self_href, data=put_data
        )

        if resp_data:
            self._set_props(self._pystac_object.from_dict(resp_data))


class Collection(EodhObject):
    _pystac_object: pystac.Collection

    def __init__(self, client: Client, headers: Headers, data: Any):
        super().__init__(client, headers, data, pystac.Collection)

    def _set_props(self, obj: pystac.Collection) -> None:
        self.id = obj.id
        self.description = obj.description
        self.extent = obj.extent
        self.title = obj.title
        self.license = obj.license
        self.keywords = obj.keywords
        self.providers = obj.providers
        self.summaries = obj.summaries
        self.assets = obj.assets

    @cached_property
    def items_href(self) -> str:
        link = self._pystac_object.get_single_link(RelType.ITEMS)
        if not link:
            raise RuntimeError("Object does not have items link!")
        return link.href

    def get_items(self) -> PaginatedList[Item]:
        return PaginatedList(
            Item,
            self._client,
            "GET",
            self.items_href,
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
        url = join_url(self.items_href, item_id)
        headers, response = self._client._request_json("GET", url)

        return Item(self._client, headers, response)

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

        _, resp_data = self._client._request_json(
            "PUT", self._pystac_object.self_href, data=put_data
        )

        if resp_data:
            self._set_props(self._pystac_object.from_dict(resp_data))

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self._pystac_object.self_href)

    def create_item(
        self,
        id: str,
        geometry: dict[str, Any] | None,
        bbox: list[float] | None,
        datetime: Datetime | None,
        properties: dict[str, Any] | None,
        collection: str | pystac.Collection | None = None,
        assets: dict[str, Any] | None = None,
    ) -> Item:

        post_data = remove_null_items(
            {
                "id": id,
                "geometry": geometry,
                "bbox": bbox,
                "datetime": datetime,
                "properties": properties,
                "collection": collection,
                "assets": assets,
            }
        )

        headers, response = self._client._request_json(
            "POST", self.items_href, data=post_data
        )
        return Item(self._client, headers, response)


class Catalog(EodhObject):
    _pystac_object: pystac.Catalog

    def __init__(self, client: Client, headers: Headers, data: Any):
        super().__init__(client, headers, data, pystac.Catalog)

    def _set_props(self, obj: pystac.Catalog) -> None:
        self.id = obj.id
        self.description = obj.description
        self.title = obj.title

    @cached_property
    def collections_href(self) -> str:
        return join_url(self._pystac_object.self_href, "collections")

    def get_collections(self) -> list[Collection]:
        """Fetches all resource catalog collections.
        Calls: GET /catalogs/{catalog_id}/collections

        Returns:
            list[Collection]: List of available collections
        """

        headers, response = self._client._request_json("GET", self.collections_href)
        if not response:
            return []
        return [
            Collection(self._client, headers, item)
            for item in response.get("collections", [])
        ]

    def get_collection(self, collection_id: str) -> Collection:
        """Fetches a resource catalog collection.
        Calls: GET /catalogs/{catalog_id}/collections/{collection_id}

        Args:
            collection_id (str): ID of a collection

        Returns:
            Collection: Collection for given ID
        """
        url = join_url(self.collections_href, collection_id)
        headers, response = self._client._request_json("GET", url)

        return Collection(self._client, headers, response)

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
    ) -> Collection:
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
            "POST", self.collections_href, data=post_data
        )
        return Collection(self._client, headers, response)


class CatalogService(EodhObject):
    _pystac_object: pystac.Catalog

    def __init__(self, client: Client, headers: Headers, data: Any):
        super().__init__(client, headers, data, pystac.Catalog)

    def _set_props(self, obj: pystac.Catalog) -> None:
        self.id = obj.id
        self.description = obj.description
        self.title = obj.title

    @cached_property
    def collections_href(self) -> str:
        return join_url(self._pystac_object.self_href, "collections")

    def get_collections(self) -> list[Collection]:
        """Fetches all resource catalog collections.
        Calls: GET /collections

        Returns:
            list[Collection]: List of available collections
        """

        headers, response = self._client._request_json("GET", self.collections_href)
        if not response:
            return []
        return [
            Collection(self._client, headers, item)
            for item in response.get("collections", [])
        ]

    def get_catalog(self, catalog_id) -> Catalog:
        url = join_url(self._pystac_object.self_href, "catalogs", catalog_id)
        headers, data = self._client._request_json("GET", url)
        return Catalog(self._client, headers, data)

    def get_catalogs(self) -> list[Catalog]:
        url = join_url(self._pystac_object.self_href, "catalogs")
        headers, data = self._client._request_json("GET", url)
        return [Catalog(self._client, headers, cat) for cat in data.get("catalogs")]

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
        url = join_url(self._pystac_object.self_href, "search")
        return PaginatedList(
            Item, self._client, "POST", url, "features", first_data=data
        )

    def get_conformance(self) -> list[str]:
        url = join_url(self._pystac_object.self_href, "conformance")
        _, response = self._client._request_json("GET", url)
        return response.get("conformsTo", [])

    def ping(self) -> str | None:
        headers, response = self._client._request_json(
            "GET", join_url(self._pystac_object.self_href, "_mgmt/ping")
        )
        return response.get("message")
