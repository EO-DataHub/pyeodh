import pytest


@pytest.fixture(scope="package")
def vcr_config():
    return {"filter_headers": ["authorization"]}
