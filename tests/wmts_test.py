import pytest

import pyeodh
from owslib.wmts import WebMapTileService
from owslib.map import wms111


@pytest.mark.vcr
def test_get_wmts() -> None:
    wmts = pyeodh.Client().get_wmts()
    assert isinstance(wmts, WebMapTileService)

    assert hasattr(wmts, "contents")
    assert hasattr(wmts, "operations")
    assert hasattr(wmts, "tilematrixsets")

    # Check if the name attribute patch is applied
    for op in wmts.operations:
        assert hasattr(op, "name")


@pytest.mark.vcr
def test_get_wms() -> None:
    wms = pyeodh.Client().get_wms()
    assert isinstance(wms, wms111.WebMapService_1_1_1)
    assert hasattr(wms, "contents")
    assert hasattr(wms, "operations")
