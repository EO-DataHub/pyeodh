from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pystac
import pytest
import requests
from pytest_mock import MockerFixture

import pyeodh
from pyeodh.resource_catalog import Item
from pyeodh.workspace import PinSet, PinSetSummary, Workspace

CEDA_CAT_ID = "public/catalogs/ceda-stac-catalogue"
PIN_SET_NAME = "pyeodh-test-pin-set"
# Small items, so the cassettes stay small
PIN_ITEM_IDS = [
    "CMIP6.ScenarioMIP.THU.CIESM.ssp585.r1i1p1f1.Amon.rsus.gr.v20200806",
    "CMIP6.ScenarioMIP.THU.CIESM.ssp585.r1i1p1f1.Amon.rlus.gr.v20200806",
    "CMIP6.ScenarioMIP.CSIRO.ACCESS-ESM1-5.ssp126.r1i1p1f1.day.uas.gn.v20210318",
]


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["Authorization"],
        "decode_compressed_response": True,
    }


@pytest.fixture
def client(api_token: str, username: str) -> pyeodh.Client:
    return pyeodh.Client(username=username, token=api_token, base_url="https://staging.eodatahub.org.uk")


@pytest.fixture
def workspace(client: pyeodh.Client) -> Workspace:
    return client.workspace


@pytest.fixture
def stac_items(client: pyeodh.Client) -> list[Item]:
    catalog = client.get_catalog_service().get_catalog(CEDA_CAT_ID)
    return list(catalog.search(collections=["cmip6"], ids=PIN_ITEM_IDS))


@pytest.fixture
def clean_pin_sets(workspace: Workspace) -> Iterator[None]:
    """Delete test pin sets left by earlier runs before the test, and the test's own after it."""

    def delete_test_pin_sets() -> None:
        for pin_set in workspace.list_pin_sets():
            if pin_set.id and pin_set.name and pin_set.name.startswith(PIN_SET_NAME):
                workspace.delete_pin_set(pin_set.id)

    delete_test_pin_sets()
    yield
    delete_test_pin_sets()


@pytest.mark.vcr
@pytest.mark.parametrize(
    "file, ws_file_path",
    [
        (b"test content", "test.txt"),
        ("tests/data/test.txt", "test.txt"),
    ],
)
def test_upload_file(workspace: Workspace, file: str | bytes, ws_file_path: str) -> None:
    workspace.upload_file(file=file, ws_file_path=ws_file_path)


def test_upload_nonexistent_file(workspace: Workspace) -> None:
    with pytest.raises(FileNotFoundError):
        workspace.upload_file(
            file="/path/to/nonexistent/file",
            ws_file_path="test.txt",
        )


def test_upload_file_mocked(mocker: MockerFixture, workspace: Workspace) -> None:
    # Test data
    test_content = b"test content"
    workspace_name = "test-workspace"
    ws_file_path = "test.txt"

    # Mock the _request_raw method
    mocker.patch.object(workspace._client, "_request_raw")
    spy = mocker.spy(workspace._client, "_request_raw")

    workspace.upload_file(file=test_content, ws_file_path=ws_file_path, workspace_name=workspace_name)
    assert spy.call_args.args[0] == "PUT"
    assert (
        spy.call_args.args[1] == f"https://{workspace_name}.staging.eodatahub-workspaces.org.uk/files/"
        f"workspaces-eodhp-staging/{ws_file_path}"
    )
    assert spy.call_args.kwargs["data"] == test_content


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_create_pin_set(workspace: Workspace, stac_items: list[Item], username: str):
    created = workspace.create_pin_set(
        PIN_SET_NAME, description="Test pin set", visibility="private", items=stac_items[:2]
    )

    assert isinstance(created, PinSet)
    assert created.id is not None
    assert created.name == PIN_SET_NAME
    assert created.description == "Test pin set"
    assert created.visibility == "private"
    assert created.workspace == username
    assert created.created_by == username
    assert isinstance(created.created_at, datetime)
    assert created.item_count == 2
    assert [(ref.collection_id, ref.item_id, ref.self_href) for ref in created.items] == [
        (item.collection, item.id, item.self_href) for item in stac_items[:2]
    ]


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_list_and_get_pin_set(workspace: Workspace, stac_items: list[Item]):
    created = workspace.create_pin_set(PIN_SET_NAME, items=stac_items[:2])
    assert created.id is not None

    summaries = workspace.list_pin_sets()
    assert all(isinstance(summary, PinSetSummary) for summary in summaries)
    summary = next(summary for summary in summaries if summary.id == created.id)
    assert summary.name == PIN_SET_NAME
    assert summary.visibility == "workspace"
    assert summary.item_count == 2

    fetched = workspace.get_pin_set(created.id)
    assert fetched.name == PIN_SET_NAME
    assert [ref.id for ref in fetched.items] == [ref.id for ref in created.items]


@pytest.mark.vcr
def test_get_non_existent_pin_set(workspace: Workspace):
    with pytest.raises(requests.exceptions.HTTPError, match="404"):
        workspace.get_pin_set("00000000-0000-0000-0000-000000000000")


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_load_pin_set_items(workspace: Workspace, stac_items: list[Item]):
    created = workspace.create_pin_set(PIN_SET_NAME, items=stac_items)
    assert created.id is not None

    loaded = workspace.get_pin_set(created.id).load_items()

    assert all(isinstance(item, Item) for item in loaded)
    assert [item.id for item in loaded] == [item.id for item in stac_items]


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_load_pin_set_items_skips_items_you_cannot_read(
    workspace: Workspace, stac_items: list[Item], caplog: pytest.LogCaptureFixture
):
    readable = stac_items[0]
    missing_href = f"{readable.self_href.rsplit('/', 1)[0]}/pyeodh-test-missing-item"
    missing = {"collectionId": readable.collection, "itemId": "pyeodh-test-missing-item", "selfHref": missing_href}
    created = workspace.create_pin_set(PIN_SET_NAME, items=[missing, readable])

    loaded = created.load_items()

    assert [item.id for item in loaded] == [readable.id]
    assert missing_href in caplog.text


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_update_pin_set(workspace: Workspace, stac_items: list[Item]):
    created = workspace.create_pin_set(PIN_SET_NAME, items=stac_items[:1])
    assert created.id is not None
    new_name = f"{PIN_SET_NAME}-renamed"

    updated = workspace.update_pin_set(created.id, name=new_name, description="Renamed", visibility="private")

    assert (updated.name, updated.description, updated.visibility) == (new_name, "Renamed", "private")
    assert [ref.id for ref in updated.items] == [ref.id for ref in created.items]


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_add_pin_set_items_skips_items_already_in_set(workspace: Workspace, stac_items: list[Item]):
    first, second, _ = stac_items
    created = workspace.create_pin_set(PIN_SET_NAME, items=[first])
    assert created.id is not None

    updated = workspace.add_pin_set_items(created.id, items=[first, pystac.Item.from_dict(second.to_dict())])

    assert [ref.item_id for ref in updated.items] == [first.id, second.id]


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_replace_pin_set_items(workspace: Workspace, stac_items: list[Item]):
    first, second, third = stac_items
    created = workspace.create_pin_set(PIN_SET_NAME, items=[first, second])
    assert created.id is not None

    replaced = workspace.replace_pin_set_items(created.id, items=[third, created.items[0]])
    assert [ref.item_id for ref in replaced.items] == [third.id, first.id]

    cleared = workspace.replace_pin_set_items(created.id, items=[])
    assert cleared.items == []
    assert cleared.item_count == 0


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_remove_pin_set_item(workspace: Workspace, stac_items: list[Item]):
    first, second, _ = stac_items
    created = workspace.create_pin_set(PIN_SET_NAME, items=[first, second])
    assert created.id is not None
    assert created.items[0].id is not None

    workspace.remove_pin_set_item(created.id, created.items[0].id)

    assert [ref.item_id for ref in workspace.get_pin_set(created.id).items] == [second.id]


@pytest.mark.vcr
@pytest.mark.usefixtures("clean_pin_sets")
def test_delete_pin_set(workspace: Workspace):
    created = workspace.create_pin_set(PIN_SET_NAME)
    assert created.id is not None

    workspace.delete_pin_set(created.id)

    with pytest.raises(requests.exceptions.HTTPError, match="404"):
        workspace.get_pin_set(created.id)


def test_pinning_item_without_self_link_raises(workspace: Workspace):
    item = pystac.Item("no-self-link", None, None, datetime(2026, 1, 1), {}, collection="test")

    with pytest.raises(ValueError, match="self link"):
        workspace.create_pin_set(PIN_SET_NAME, items=[item])
