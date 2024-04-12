import pyeodh


def test_version() -> None:
    """Tests the application version is importable."""
    assert pyeodh.__version__
