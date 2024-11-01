from __future__ import annotations

import logging
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal, TypeVar

import pystac
import pystac.catalog
from pystac import Extent, RelType, STACObject, STACTypeError, Summaries
from pystac.asset import Asset
from pystac.provider import Provider

from pyeodh import consts
from pyeodh.eodh_object import EodhObject, is_optional
from pyeodh.pagination import PaginatedList
from pyeodh.types import Headers, SearchFields, SearchSortField
from pyeodh.utils import ConformanceError, join_url, remove_null_items

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from datetime import datetime as Datetime

    from pyeodh.client import Client

logger = logging.getLogger(__name__)


C = TypeVar("C", bound="STACObject")


class Conformance(Enum):
    TRANSACTION_EXTENSION = (
        "https://api.stacspec.org/v1.0.0/ogcapi-features/extensions/transaction"
    )


class Item(EodhObject):
    _pystac_object: pystac.Item

    def __init__(self, client: Client, headers: Headers, data: Any, **kwargs):
        super().__init__(client, headers, data, pystac.Item, **kwargs)

    def _set_props(self, obj: pystac.Item) -> None:
        self.id = obj.id
        self.geometry = obj.geometry
        self.bbox = obj.bbox
        self.datetime = obj.datetime
        self.properties = obj.properties
        self.collection = obj.collection_id
        self.assets = obj.assets

    def delete(self) -> None:
        """Delete this item.


        Calls: DELETE /catalogs/{catalog_id}/collections/{collection_id}/items/{item_id}
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
        self._client._request_raw("DELETE", self._pystac_object.self_href)

    def update(
        self,
        geometry: dict[str, Any] | None = None,
        bbox: list[float] | None = None,
        datetime: Datetime | None = None,
        properties: dict[str, Any] | None = None,
        collection: str | pystac.Collection | None = None,
        assets: dict[str, Any] | None = None,
    ) -> None:
        """Update this item's attributes with new values. Only provide the values you
        want to update.

        Calls: PUT /catalogs/{catalog_id}/collections/{collection_id}/items/{item_id}


        Args:
            geometry (dict[str, Any] | None, optional): Geometry. Defaults to None.
            bbox (list[float] | None, optional): Bounding box. Defaults to None.
            datetime (Datetime | None, optional): Datetime. Defaults to None.
            properties (dict[str, Any] | None, optional): Properties. Defaults to None.
            collection (str | pystac.Collection | None, optional): Collection. Defaults
                to None.
            assets (dict[str, Any] | None, optional): Assets. Defaults to None.
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )

        put_data = remove_null_items(
            {
                "id": self.id,
                "geometry": geometry or self.geometry,  # ! getting 500 with this
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

    def __init__(self, client: Client, headers: Headers, data: Any, **kwargs):
        super().__init__(client, headers, data, pystac.Collection, **kwargs)

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
        """URL pointing to items endpoint."""
        link = self._pystac_object.get_single_link(RelType.ITEMS)
        if not link:
            raise RuntimeError("Object does not have items link!")
        return link.href

    def get_items(self) -> PaginatedList[Item]:
        """Fetches all items within a collection.

        Calls: GET /catalogs/{catalog_id}/collections/{collection_id}/items

        Returns:
            PaginatedList[Item]: Iterable list of items. Automatically handles
                paginated results.
        """
        return PaginatedList(
            Item,
            self._client,
            "GET",
            self.items_href,
            "features",
            params={"limit": consts.PAGINATION_LIMIT},
            parent=self,
        )

    def get_item(self, item_id: str) -> Item:
        """Fetches a collection item.

        Calls: GET /catalogs/{catalog_id}/collections/{collection_id}/items/{item_id}

        Args:
            item_id (str): ID of a collection item.

        Returns:
            Item: Initialized item object.
        """
        url = join_url(self.items_href, item_id)
        headers, response = self._client._request_json("GET", url)

        return Item(self._client, headers, response, parent=self)

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
        """Update collection attributes with new values. Provide only the values you
        want to update.

        Calls: PUT /catalogs/{catalog_id}/collections/{collection_id}


        Args:
            description (str | None, optional): Description. Defaults to None.
            extent (Extent | None, optional): Extent. Defaults to None.
            title (str | None, optional): Title. Defaults to None.
            license (str | None, optional): License. Defaults to None.
            keywords (list[str] | None, optional): Keywords. Defaults to None.
            providers (list[Provider] | None, optional): Providers. Defaults to None.
            summaries (Summaries | None, optional): Summaries. Defaults to None.
            assets (dict[str, Asset] | None, optional): Assets. Defaults to None.
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
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
        """Delete this collection.

        Calls: DELETE /catalogs/{catalog_id}/collections/{collection_id}
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
        self._client._request_raw("DELETE", self._pystac_object.self_href)

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
        """Create an item as part of this collection.

        Calls: POST /catalogs/{catalog_id}/collections/{collection_id}/items/{item_id}

        Args:
            id (str): A unique ID.
            geometry (dict[str, Any] | None): Geometry
            bbox (list[float] | None): Bounding box
            datetime (Datetime | None): Datetime
            properties (dict[str, Any] | None): Properties
            collection (str | pystac.Collection | None, optional): ID of a parent
                collection. Defaults to None.
            assets (dict[str, Any] | None, optional): Assets. Defaults to None.

        Returns:
            Item: _description_
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
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
        return Item(self._client, headers, response, parent=self)


class Catalog(EodhObject):
    _pystac_object: pystac.Catalog

    def __init__(self, client: Client, headers: Headers, data: Any, **kwargs):
        super().__init__(client, headers, data, pystac.Catalog, **kwargs)

    def _set_props(self, obj: pystac.Catalog) -> None:
        self.id = obj.id
        self.description = obj.description
        self.title = obj.title
        self.conforms_to = obj.extra_fields.get("conformsTo", []).copy()

    @cached_property
    def collections_href(self) -> str:
        """URL pointing to collections endpoint."""
        return join_url(self._pystac_object.self_href, "collections")

    def get_catalogs(self) -> list[Catalog]:
        """Fetches children catalogs of this parent catalog.

        Calls: GET /catalogs/{catalog_path}/catalogs

        Returns:
            list[Catalog]: List of children catalogs.
        """
        url = join_url(self._pystac_object.self_href, "catalogs")
        headers, data = self._client._request_json("GET", url)
        catalogs = []

        for cat in data.get("catalogs"):
            try:
                catalogs.append(Catalog(self._client, headers, cat, parent=self))
            except STACTypeError as e:
                logger.warning(f"{e} => Skipping")
        return catalogs

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
            Collection(self._client, headers, item, parent=self)
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

        return Collection(self._client, headers, response, parent=self)

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
        """Create a new collection inside a catalog.

        Calls: POST /catalogs/{catalog_id}/collections

        Args:
            id (str)
            description (str)
            extent (Extent)
            title (str | None, optional): Defaults to None.
            license (str | None, optional): Defaults to None.
            keywords (list[str] | None, optional): Defaults to None.
            providers (list[Provider] | None, optional): Defaults to None.
            summaries (Summaries | None, optional): Defaults to None.
            assets (dict[str, Asset] | None, optional): Defaults to None.

        Returns:
            Collection: An initialized collection object.
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
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
        return Collection(self._client, headers, response, parent=self)

    def update(
        self,
        description: str | None = None,
        title: str | None = None,
    ) -> None:
        """Updates catalog.

        Calls: PUT /catalogs/{catalog_id}

        Args:
            description (str | None, optional): New description.  Defaults to None.
            title (str | None, optional): New title. Defaults to None.
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
        assert is_optional(description, str), description
        assert is_optional(title, str), title

        put_data = remove_null_items(
            {
                "id": self.id,
                "description": description or self.description,
                "title": title or self.title,
            }
        )
        _, resp_data = self._client._request_json(
            "PUT", self._pystac_object.self_href, data=put_data
        )

        if resp_data:
            self._set_props(self._pystac_object.from_dict(resp_data))

    def delete(self) -> None:
        """Delete this catalog.

        Calls: DELETE /catalogs/{catalog_id}
        """
        if not self.get_root().check_conforms_to(
            Conformance.TRANSACTION_EXTENSION.value
        ):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
        self._client._request_raw("DELETE", self._pystac_object.self_href)

    def search(
        self,
        limit: int = consts.PAGINATION_LIMIT,
        collections: list[str] | None = None,
        catalog_paths: list[str] | None = None,
        ids: list[str] | None = None,
        bbox: list[Any] | None = None,
        intersects: dict | None = None,
        datetime: str | None = None,
        fields: SearchFields | None = None,
        query: dict[str, Any] | list[str] | None = None,
        sort_by: list[SearchSortField] | None = None,
        filter: dict | None = None,
        filter_crs: str | None = None,
        filter_lang: Literal["cql-json", "cql2-json", "cql2-text"] | None = None,
    ) -> PaginatedList[Item]:
        assert isinstance(limit, int), limit
        assert is_optional(collections, list), collections
        assert is_optional(catalog_paths, list), catalog_paths
        assert is_optional(ids, list), ids
        assert is_optional(bbox, list), bbox
        # assert is_optional(intersects, dict), intersects
        assert is_optional(datetime, str), datetime
        assert is_optional(fields, dict), fields
        assert is_optional(query, (dict, list)), query
        assert is_optional(sort_by, list), sort_by
        assert is_optional(filter, dict), filter
        assert is_optional(filter_crs, str), filter_crs
        assert filter_lang in ["cql-json", "cql2-json", "cql2-text", None]

        data = remove_null_items(
            {
                "limit": limit,
                "catalog_paths": catalog_paths,
                "collections": collections,
                "ids": ids,
                "bbox": bbox,
                "intersects": self._format_intersects(intersects),
                "datetime": datetime,
                "fields": fields,
                "query": self._make_query_dict(query),
                "sortby": sort_by,
                "filter": filter,
                "filter_crs": filter_crs,
                "filter_lang": filter_lang,
            }
        )
        url = join_url(self._pystac_object.self_href, "search")
        return PaginatedList(
            Item, self._client, "POST", url, "features", first_data=data, parent=self
        )


class CatalogService(Catalog):

    def get_collections(self) -> list[Collection]:
        """Fetches all resource catalog collections.

        Calls: GET /collections

        Returns:
            list[Collection]: List of available collections
        """
        return super().get_collections()

    def get_catalog(self, catalog_id: str) -> Catalog:
        """Fetches a catalog.

        Calls: GET /catalogs/{catalog_id}

        Args:
            catalog_id (str): Catalog ID

        Returns:
            Catalog: An initialized resource catalog object.
        """

        url = join_url(self._pystac_object.self_href, "catalogs", catalog_id)
        headers, data = self._client._request_json("GET", url)
        return Catalog(self._client, headers, data, parent=self)

    def get_catalogs(self) -> list[Catalog]:
        """Fetches all catalogs.

        Calls: GET /catalogs

        Returns:
            list[Catalog]: List of all catalogs available.
        """
        return super().get_catalogs()

    def create_catalog(
        self,
        id: str,
        description: str,
        title: str | None = None,
    ) -> Catalog:
        """Creates a new catalog

        Calls: POST /catalogs

        Args:
            id (str): New catalog ID
            description (str): Catalog description
            title (str | None, optional): Catalog title. Defaults to None.

        Returns:
            Catalog: An initialized catalog object.
        """
        if not self.check_conforms_to(Conformance.TRANSACTION_EXTENSION.value):
            raise ConformanceError(
                f"{Conformance.TRANSACTION_EXTENSION.value}",
            )
        assert isinstance(id, str), id
        assert isinstance(description, str), description
        assert is_optional(title, str), title

        post_data = remove_null_items(
            {
                "id": id,
                "description": description,
                "title": title,
            }
        )
        headers, response = self._client._request_json(
            "POST", self.collections_href, data=post_data
        )
        return Catalog(self._client, headers, response, parent=self)

    def collection_search(
        self,
        limit: int = consts.PAGINATION_LIMIT,
        bbox: list[Any] | None = None,
        datetime: str | None = None,
        query: str | None = None,
    ) -> PaginatedList[Collection]:
        """Searches the catalog for collections.

        Args:
            limit (int, optional): Number of results per page. Defaults to
                consts.PAGINATION_LIMIT.
            bbox (list[Any] | None, optional): Bounding box. Defaults to None.
            datetime (str | None, optional): Datetime. Defaults to None.
            query (str | None, optional): Query string. Defaults to None.

        Returns:
            PaginatedList[Collection]: Iterable list of collections.
        """

        assert isinstance(limit, int), limit
        assert is_optional(bbox, list), bbox
        assert is_optional(datetime, str), datetime
        assert is_optional(query, str), query

        data = remove_null_items(
            {
                "limit": limit,
                "bbox": bbox,
                "datetime": datetime,
                "q": query,
            }
        )
        url = join_url(self._pystac_object.self_href, "collection-search")
        return PaginatedList(
            Collection,
            self._client,
            "POST",
            url,
            "collections",
            first_data=data,
            parent=self,
        )

    def discovery_search(
        self,
        query: str,
        limit: int = consts.PAGINATION_LIMIT,
    ) -> PaginatedList[Catalog]:
        """Searches the catalog for catalogs and collections.

        Args:
            limit (int, optional): Number of results per page. Defaults to
                consts.PAGINATION_LIMIT.
            query (str | None, optional): Query string. Defaults to None.

        Returns:
            PaginatedList[Collection]: Iterable list of collections.
        """

        assert isinstance(query, str), query
        assert isinstance(limit, int), limit

        data = remove_null_items(
            {
                "limit": limit,
                "q": query,
            }
        )
        url = join_url(self._pystac_object.self_href, "discovery-search")

        return PaginatedList(
            Catalog,
            self._client,
            "POST",
            url,
            "catalogs_and_collections",
            first_data=data,
            parent=self,
        )

    def get_conformance(self) -> list[str]:
        """Fetches list of standards the API conforms to.

        Calls: GET /conformance

        Returns:
            list[str]: Standards.
        """
        url = join_url(self._pystac_object.self_href, "conformance")
        _, response = self._client._request_json("GET", url)
        return response.get("conformsTo", [])

    def ping(self) -> str | None:
        """Pings API.

        Calls: GET /_mgmt/ping

        Returns:
            str | None: Pong.
        """
        headers, response = self._client._request_json(
            "GET", join_url(self._pystac_object.self_href, "_mgmt/ping")
        )
        return response.get("message")

    def check_conforms_to(self, conformance_uri: str | Conformance) -> bool:
        """Test if API conforms to a specification.

        Args:
            conformance_uri (str | Conformance): URI of the specification

        Returns:
            bool
        """
        return conformance_uri in self.get_conformance()
