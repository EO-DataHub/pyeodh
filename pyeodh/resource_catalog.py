from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal, Type, TypeVar

from pystac import Catalog, Collection, Extent, Item, RelType, STACObject, Summaries
from pystac.asset import Asset
from pystac.provider import Provider

from pyeodh import consts
from pyeodh.api_mixin import ApiMixin, is_optional
from pyeodh.pagination import PaginatedList
from pyeodh.types import Headers, SearchFields, SearchSortField
from pyeodh.utils import join_url, remove_null_items

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from datetime import datetime as Datetime

    from pyeodh.client import Client

C = TypeVar("C", bound="STACObject")


class EodhItem(Item, ApiMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def _from_dict(
        cls: Type[C], client: Client, headers: Headers, raw_data: dict[str, Any]
    ) -> C:
        item = super().from_dict(raw_data)
        ApiMixin.__init__(item, client=client, headers=headers, data=raw_data)
        return item

    def _update_properties(self, obj: Item) -> None:
        self.__dict__.update(obj.__dict__)

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self.self_href)

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

        _, resp_data = self._client._request_json("PUT", self.self_href, data=put_data)

        if resp_data:
            self._update_properties(
                self._from_dict(self._client, self._headers, resp_data)
            )


class EodhCollection(Collection, ApiMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def _from_dict(
        cls: Type[C], client: Client, headers: Headers, raw_data: dict[str, Any]
    ) -> C:
        col = super().from_dict(raw_data)
        ApiMixin.__init__(col, client=client, headers=headers, data=raw_data)
        return col

    def _update_properties(self, obj: Collection) -> None:
        self.__dict__.update(obj.__dict__)

    @cached_property
    def items_href(self) -> str:
        link = self.get_single_link(RelType.ITEMS)
        if not link:
            raise RuntimeError("Object does not have items link!")
        return link.href

    def get_items(self) -> PaginatedList[EodhItem]:
        return PaginatedList(
            EodhItem,
            self._client,
            "GET",
            self.items_href,
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
        url = join_url(self.items_href, item_id)
        headers, response = self._client._request_json("GET", url)

        return EodhItem._from_dict(self._client, headers, response)

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

        _, resp_data = self._client._request_json("PUT", self.self_href, data=put_data)

        if resp_data:
            self._update_properties(
                self._from_dict(self._client, self._headers, resp_data)
            )

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self.self_href)

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
            "POST", self.items_href, data=post_data
        )
        return EodhItem._from_dict(self._client, headers, response)


class EodhCatalog(Catalog, ApiMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def _from_dict(
        cls: Type[C], client: Client, headers: Headers, raw_data: dict[str, Any]
    ) -> C:
        cat = super().from_dict(raw_data)
        ApiMixin.__init__(cat, client=client, headers=headers, data=raw_data)
        return cat

    @cached_property
    def collections_href(self) -> str:
        link = self.get_single_link("data")
        if not link:
            raise RuntimeError("Object does not have collections link!")
        return link.href

    def get_collections(self) -> list[EodhCollection]:
        """Fetches all resource catalog collections.
        Calls: GET /collections

        Returns:
            list[Collection]: List of available collections
        """

        headers, response = self._client._request_json("GET", self.collections_href)
        if not response:
            return []
        return [
            EodhCollection._from_dict(self._client, headers, item)
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
        url = join_url(self.collections_href, collection_id)
        headers, response = self._client._request_json("GET", url)

        return EodhCollection._from_dict(self._client, headers, response)

    def get_conformance(self) -> list[str]:
        url = join_url(self.self_href, "conformance")
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
        url = join_url(self.self_href, "search")
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
            "POST", self.collections_href, data=post_data
        )
        return EodhCollection._from_dict(self._client, headers, response)

    def ping(self) -> str | None:
        headers, response = self._client._request_json(
            "GET", join_url(self.self_href, "_mgmt/ping")
        )
        return response.get("message")
