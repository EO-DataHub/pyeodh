import pytest

import pyeodh
import pyeodh.pagination
import pyeodh.resource_catalog


@pytest.mark.vcr
def test_get_catalog_service():
    svc = pyeodh.Client().get_catalog_service()
    assert svc._pystac_object.STAC_OBJECT_TYPE == "Catalog"
    assert (
        svc._pystac_object.self_href
        == "https://test.eodatahub.org.uk/api/catalogue/stac/"
    )


@pytest.mark.vcr
def test_ping():
    svc = pyeodh.Client().get_catalog_service()
    msg = svc.ping()
    assert msg == "PONG"


@pytest.mark.vcr
def test_get_conformance():
    svc = pyeodh.Client().get_catalog_service()
    conformances = svc.get_conformance()
    assert isinstance(conformances, list)
    assert all(isinstance(elem, str) for elem in conformances)


@pytest.mark.vcr
def test_get_catalog():
    svc = pyeodh.Client().get_catalog_service()
    cat = svc.get_catalog("supported-datasets")
    assert cat.id == "supported-datasets"


@pytest.mark.vcr
def test_get_catalogs_from_catalog():
    svc = pyeodh.Client().get_catalog_service()
    parent_catalog = svc.get_catalog("supported-datasets")
    children = parent_catalog.get_catalogs()
    assert isinstance(children, list)
    assert all(isinstance(elem, pyeodh.resource_catalog.Catalog) for elem in children)


@pytest.mark.vcr
def test_get_collections_from_catalog():
    svc = pyeodh.Client().get_catalog_service()
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collections = cat.get_collections()
    assert isinstance(collections, list)
    assert all(
        isinstance(elem, pyeodh.resource_catalog.Collection) for elem in collections
    )


@pytest.mark.vcr
def test_get_collection_from_catalog():
    svc = pyeodh.Client().get_catalog_service()
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    assert collection.id == "cmip6"


@pytest.mark.vcr
def test_get_collection_items():
    svc = pyeodh.Client().get_catalog_service()
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    assert isinstance(items, pyeodh.pagination.PaginatedList)
    assert all(isinstance(elem, pyeodh.resource_catalog.Item) for elem in items)


@pytest.mark.vcr
def test_get_collection_item():
    svc = pyeodh.Client().get_catalog_service()
    cat = svc.get_catalog("supported-datasets/ceda-stac-fastapi")
    collection = cat.get_collection("cmip6")
    items = collection.get_items()
    item = collection.get_item(items[0].id)
    assert isinstance(item, pyeodh.resource_catalog.Item)
    assert item.id == items[0].id
