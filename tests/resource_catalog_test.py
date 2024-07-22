import pyeodh
from vcr import VCR

vcr = VCR(
    cassette_library_dir="tests/cassettes",
    path_transformer=VCR.ensure_suffix(".yaml"),
    filter_headers=["authorization"],
)


@vcr.use_cassette()
def test_get_catalog_service():
    svc = pyeodh.Client().get_catalog_service()
    assert svc._pystac_object.STAC_OBJECT_TYPE == "Catalog"
    assert (
        svc._pystac_object.self_href
        == "https://test.eodatahub.org.uk/api/catalogue/stac/"
    )
