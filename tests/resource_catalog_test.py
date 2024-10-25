from unittest.mock import patch

import pytest
from pystac import Extent

import pyeodh
import pyeodh.pagination
import pyeodh.resource_catalog
from pyeodh import consts
from pyeodh.resource_catalog import CatalogService
from pyeodh.utils import ConformanceError


@pytest.fixture
def svc() -> CatalogService:
    return pyeodh.Client().get_catalog_service()


@pytest.mark.vcr
def test_get_catalog_service(svc: CatalogService):
    assert svc._pystac_object.STAC_OBJECT_TYPE == "Catalog"
    assert (
        svc._pystac_object.self_href
        == "https://test.eodatahub.org.uk/api/catalogue/stac/"
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
    cat = svc.get_catalog("supported-datasets")
    assert cat.id == "supported-datasets"


@pytest.mark.vcr
def test_get_catalogs_from_catalog(svc: CatalogService):
    parent_catalog = svc.get_catalog("supported-datasets")
    children = parent_catalog.get_catalogs()
    assert isinstance(children, list)
    assert all(isinstance(elem, pyeodh.resource_catalog.Catalog) for elem in children)


@pytest.mark.vcr
def test_get_collections_from_catalog(svc: CatalogService):
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collections = cat.get_collections()
    assert isinstance(collections, list)
    assert all(
        isinstance(elem, pyeodh.resource_catalog.Collection) for elem in collections
    )


@pytest.mark.vcr
def test_get_collection_from_catalog(svc: CatalogService):
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    assert collection.id == "cmip6"


@pytest.mark.vcr
def test_get_collection_items(svc: CatalogService):
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    assert isinstance(items, pyeodh.pagination.PaginatedList)

    for i in range(20):
        assert isinstance(items[i], pyeodh.resource_catalog.Item)


@pytest.mark.vcr
def test_get_collection_items_with_limit(svc: CatalogService):
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    items = collection.get_items().get_limited()
    assert len(items) == consts.PAGINATION_LIMIT


@pytest.mark.vcr
def test_get_collection_items_total_count(svc: CatalogService):
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    assert isinstance(items.total_count, int)


@pytest.mark.vcr
def test_get_collection_item(svc: CatalogService):
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    item = collection.get_item(items[0].id)
    assert isinstance(item, pyeodh.resource_catalog.Item)
    assert item.id == items[0].id


@pytest.mark.vcr
@patch(
    "pyeodh.resource_catalog.CatalogService.get_conformance",
    return_value=["https://api.stacspec.org/v1.0.0/core"],
)
def test_conformance_error_raised(mock_get_conformance, svc: CatalogService):
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
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
