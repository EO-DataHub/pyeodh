from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pyeodh.utils import s3_url

if TYPE_CHECKING:
    from pyeodh.client import Client


class Workspace:
    """Contains methods for interacting with EODH workspaces."""

    def __init__(self, client: Client):
        self._client = client

    def upload_file(
        self,
        file: str | bytes,
        ws_file_path: str,
        workspace_name: str | None = None,
    ) -> None:
        """Upload a file to a workspace.

        Args:
            workspace_name (str): Name of the workspace
            file (str | bytes): Path to the file to upload or bytes to upload
            ws_file_path (str): Path to the file within the workspace
        """

        if self._client.token is None:
            raise ValueError(
                "Valid token is required for accessing protected API endpoints."
            )

        if workspace_name is None:
            workspace_name = self._client.username
        if workspace_name is None:
            raise ValueError("Workspace name is required")

        url = s3_url(workspace_name, ws_file_path)

        if isinstance(file, str):
            if not Path(file).is_file():
                raise FileNotFoundError(f"File not found: {file}")
            with open(file, "rb") as f:
                file_content = f.read()
        elif isinstance(file, bytes):
            file_content = file
        else:
            raise TypeError("Invalid file type")

        def encode_file(f: bytes) -> tuple[str, bytes]:
            return ("application/octet-stream", f)

        self._client._request_raw("PUT", url, data=file_content, encode=encode_file)
