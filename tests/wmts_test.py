import pytest
from owslib.wmts import WebMapTileService

import pyeodh


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["Authorization"],
        "decode_compressed_response": True,
    }


@pytest.mark.vcr
def test_get_wmts() -> None:
    wmts = (
        pyeodh.Client()
        .get_catalog_service()
        .get_catalog("public/catalogs/ceda-stac-catalogue")
        .get_wmts()
    )
    assert isinstance(wmts, WebMapTileService)

    assert hasattr(wmts, "contents")
    assert hasattr(wmts, "operations")
    assert hasattr(wmts, "tilematrixsets")

    # Check if the name attribute patch is applied
    for op in wmts.operations:
        assert hasattr(op, "name")
