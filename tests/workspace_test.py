from typing import Union

import pytest
from pytest_mock import MockerFixture

import pyeodh
from pyeodh.workspace import Workspace


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["Authorization"],
        "decode_compressed_response": True,
    }


@pytest.fixture
def workspace(api_token: str, username: str) -> Workspace:
    return pyeodh.Client(username=username, token=api_token).workspace


@pytest.mark.vcr
@pytest.mark.parametrize(
    "file, ws_file_path",
    [
        (b"test content", "test.txt"),
        ("tests/data/test.txt", "test.txt"),
    ],
)
def test_upload_file(
    workspace: Workspace, file: Union[str, bytes], ws_file_path: str
) -> None:
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

    workspace.upload_file(
        file=test_content, ws_file_path=ws_file_path, workspace_name=workspace_name
    )
    assert spy.call_args.args[0] == "PUT"
    assert (
        spy.call_args.args[1]
        == f"https://{workspace_name}.staging.eodatahub-workspaces.org.uk/files/"
        f"workspaces-eodhp-staging/{ws_file_path}"
    )
    assert spy.call_args.kwargs["data"] == test_content
