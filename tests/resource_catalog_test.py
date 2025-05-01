from unittest.mock import patch

import pytest
from pystac import Extent

import pyeodh
import pyeodh.pagination
import pyeodh.resource_catalog
from pyeodh import consts
from pyeodh.resource_catalog import CatalogService, Item
from pyeodh.utils import ConformanceError

CEDA_CAT_ID = "public/catalogs/ceda-stac-catalogue"


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["Authorization"],
        "decode_compressed_response": True,
    }


@pytest.fixture
def svc() -> CatalogService:
    return pyeodh.Client().get_catalog_service()


@pytest.mark.vcr
def test_get_catalog_service(svc: CatalogService):
    assert svc._pystac_object.STAC_OBJECT_TYPE == "Catalog"
    assert (
        svc._pystac_object.self_href
        == "https://staging.eodatahub.org.uk/api/catalogue/stac/"
    )


@pytest.mark.vcr
def test_ping(svc: CatalogService):
    msg = svc.ping()
    assert msg == "PONG"


@pytest.mark.vcr
def test_get_conformance(svc: CatalogService):
    conformances = svc.get_conformance()
    assert isinstance(conformances, list)
    assert all(isinstance(elem, str) for elem in conformances)


@pytest.mark.vcr
def test_get_catalog(svc: CatalogService):
    cat = svc.get_catalog("public")
    assert cat.id == "public"


@pytest.mark.vcr
def test_get_catalogs_from_catalog(svc: CatalogService):
    parent_catalog = svc.get_catalog("public")
    children = parent_catalog.get_catalogs()
    assert isinstance(children, list)
    assert all(isinstance(elem, pyeodh.resource_catalog.Catalog) for elem in children)


@pytest.mark.vcr
def test_get_collections_from_catalog(svc: CatalogService):
    cat = svc.get_catalog(CEDA_CAT_ID)
    collections = cat.get_collections()
    assert isinstance(collections, list)
    assert all(
        isinstance(elem, pyeodh.resource_catalog.Collection) for elem in collections
    )


@pytest.mark.vcr
def test_get_collection_from_catalog(svc: CatalogService):
    cat = svc.get_catalog(CEDA_CAT_ID)
    collection = cat.get_collection("cmip6")
    assert collection.id == "cmip6"


@pytest.mark.vcr
def test_get_collection_items(svc: CatalogService):
    cat = svc.get_catalog(CEDA_CAT_ID)
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    assert isinstance(items, pyeodh.pagination.PaginatedList)

    for i in range(20):
        assert isinstance(items[i], pyeodh.resource_catalog.Item)


@pytest.mark.vcr
def test_get_collection_items_with_limit(svc: CatalogService):
    cat = svc.get_catalog(CEDA_CAT_ID)
    collection = cat.get_collection("cmip6")
    items = collection.get_items().get_limited()
    assert len(items) == consts.PAGINATION_LIMIT


@pytest.mark.vcr
def test_get_collection_items_total_count(svc: CatalogService):
    cat = svc.get_catalog(CEDA_CAT_ID)
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    assert isinstance(items.total_count, int)


@pytest.mark.vcr
def test_get_collection_item(svc: CatalogService):
    cat = svc.get_catalog(CEDA_CAT_ID)
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    item = collection.get_item(items[0].id)
    assert isinstance(item, pyeodh.resource_catalog.Item)
    assert item.id == items[0].id


# @pytest.mark.vcr
# def test_get_cloud_product(svc: CatalogService):
#     import xarray
#     from ceda_datapoint.core.cloud import DataPointCloudProduct

#     cat = svc.get_catalog(CEDA_CAT_ID)
#     collection = cat.get_collection("cmip6")
#     items = collection.get_items()
#     item = collection.get_item(items[0].id)

#     product = item.get_cloud_products()
#     assert isinstance(product, DataPointCloudProduct)
#     assert item.id in product.id

#     ds = product.open_dataset()
#     assert isinstance(ds, xarray.Dataset)


@pytest.mark.vcr
def test_get_item_from_href(svc: CatalogService):
    item = pyeodh.resource_catalog.Item.from_href(
        svc._client,
        "https://staging.eodatahub.org.uk/api/catalogue/stac/catalogs/public/catalogs/"
        "ceda-stac-catalogue/collections/sentinel2_ard/items/neodc.sentinel_ard.data."
        "sentinel_2.2025.04.11.S2A_20250411_latn572lonw0021_T30VWJ_ORB123_20250411183"
        "553_utm30n_osgb",
    )
    assert isinstance(item, pyeodh.resource_catalog.Item)
    assert (
        item.id == "neodc.sentinel_ard.data.sentinel_2.2025.04.11."
        "S2A_20250411_latn572lonw0021_T30VWJ_ORB123_20250411183553_utm30n_osgb"
    )


@pytest.mark.vcr
@patch(
    "pyeodh.resource_catalog.CatalogService.get_conformance",
    return_value=["https://api.stacspec.org/v1.0.0/core"],
)
def test_conformance_error_raised(mock_get_conformance, svc: CatalogService):
    cat = svc.get_catalog(CEDA_CAT_ID)
    collection = cat.get_collection("cmip6")
    item = collection.get_items()[0]
    # Test Catalog methods
    with pytest.raises(ConformanceError):
        svc.create_catalog("test_id", "test_description")
    with pytest.raises(ConformanceError):
        cat.update(description="new description")
    with pytest.raises(ConformanceError):
        cat.delete()

    # Test Collection methods
    with pytest.raises(ConformanceError):
        cat.create_collection(
            "test_id",
            "test_description",
            Extent.from_dict(
                {
                    "spatial": {
                        "bbox": [
                            [
                                -9.00034454651177,
                                49.48562028352171,
                                3.1494256015866995,
                                61.33444247301668,
                            ]
                        ]
                    },
                    "temporal": {
                        "interval": [["2023-01-01T11:14:51Z", "2023-11-01T11:43:49Z"]]
                    },
                }
            ),
        )
    with pytest.raises(ConformanceError):
        collection.update(description="new description")
    with pytest.raises(ConformanceError):
        collection.delete()

    # Test Item methods
    with pytest.raises(ConformanceError):
        collection.create_item("test_id", None, None, None, {})
    with pytest.raises(ConformanceError):
        item.update(properties={"new": "property"})
    with pytest.raises(ConformanceError):
        item.delete()
    # with pytest.raises(ConformanceError):
    #    _ = item.get_cloud_products()


@patch("pyeodh.client.Client._request_json")
def test_from_href_mocked(mock_request_json, svc: CatalogService):
    href = "https://example.com/api/stac/item1"

    # Mock response data
    mock_response_data = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "item1",
        "collection": "collection1",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 90], [0, -90], [-180, -90], [-180, 90], [0, 90]]],
        },
        "bbox": [0, 90, 0, -90],
        "properties": {
            "datetime": "2023-11-20T11:23:51Z",
            "updated": "2024-11-05T07:43:53.975696Z",
            "start_datetime": "2023-11-20T11:23:51Z",
            "end_datetime": "2023-11-20T11:23:51Z",
        },
        "links": [
            {
                "rel": "self",
                "type": "application/geo+json",
                "href": "https://example.com/api/stac/item1",
            }
        ],
        "assets": {},
    }

    # Mock the _request_json method to return the mock response
    mock_request_json.return_value = (None, mock_response_data)

    item = Item.from_href(svc._client, href)
    assert isinstance(item, Item)
    assert item.id == mock_response_data["id"]
