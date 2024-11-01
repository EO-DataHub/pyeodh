import os

import dotenv
import pytest
from pytest_mock import MockerFixture

import pyeodh
from pyeodh.workspace import Workspace


@pytest.fixture(scope="module")
def vcr_config():
    return {"filter_headers": ["Authorization"]}


@pytest.fixture
def workspace() -> Workspace:
    dotenv.load_dotenv()
    username = os.getenv("ADES_USER", "figi44")
    token = os.getenv("ADES_TOKEN", "test_token")
    return pyeodh.Client(username=username, token=token).workspace


@pytest.mark.vcr
@pytest.mark.parametrize(
    "file, ws_file_path",
    [
        (b"test content", "test.txt"),
        ("tests/data/test.txt", "test.txt"),
    ],
)
def test_upload_file(
    workspace: Workspace, file: str | bytes, ws_file_path: str
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
        == f"https://{workspace_name}.workspaces.test.eodhp.eco-ke-staging.com/files/"
        f"eodhp-test-workspaces1/{ws_file_path}"
    )
    assert spy.call_args.kwargs["data"] == test_content
