from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from pyeodh.eodh_object import EodhObject
from pyeodh.resource_catalog import Item
from pyeodh.utils import join_url, s3_url

if TYPE_CHECKING:
    from pyeodh.client import Client
    from pyeodh.types import Headers

logger = logging.getLogger(__name__)


class PinSetItem(EodhObject):
    """Represents a reference to a STAC item in a pin set. Use `load` to fetch the item
    itself.

    Args:
        client (Client): Instance of pyeodh request client
        headers (Headers): Response headers received when requesting this record
        data (Any): Raw response data received when requesting this record
    """

    def __init__(self, client: Client, headers: Headers, data: dict, **kwargs: Any) -> None:
        super().__init__(client, headers, data, **kwargs)

    def _set_props(self, obj: dict) -> None:
        self.id = self._make_str_prop(obj.get("id"))
        self.collection_id = self._make_str_prop(obj.get("collectionId"))
        self.item_id = self._make_str_prop(obj.get("itemId"))
        self.self_href = self._make_str_prop(obj.get("selfHref"))
        # UI-only state such as render settings and opacity
        self.display: dict[str, Any] | None = obj.get("display")
        self.position = self._make_int_prop(obj.get("position"))
        self.added_at = self._make_datetime_prop(obj.get("addedAt"))

    def load(self) -> Item:
        """Fetch the referenced STAC item from its selfHref. The resource catalog checks
        your own access to the item.

        Calls: GET {self_href}

        Returns:
            Item: The STAC item.
        """
        if self.self_href is None:
            raise ValueError(f"Pin set item {self.id} does not have a selfHref")
        headers, response = self._client._request_json("GET", self.self_href)
        return Item(self._client, headers, response)


class PinSetSummary(EodhObject):
    """Represents a pin set, a named list of pinned STAC items in a workspace, without its
    items. Use `Workspace.get_pin_set` to get the items.

    Args:
        client (Client): Instance of pyeodh request client
        headers (Headers): Response headers received when requesting this record
        data (Any): Raw response data received when requesting this record
    """

    def __init__(self, client: Client, headers: Headers, data: dict, **kwargs: Any) -> None:
        super().__init__(client, headers, data, **kwargs)

    def _set_props(self, obj: dict) -> None:
        self.id = self._make_str_prop(obj.get("id"))
        self.workspace = self._make_str_prop(obj.get("workspace"))
        self.name = self._make_str_prop(obj.get("name"))
        self.description = self._make_str_prop(obj.get("description"))
        self.visibility = self._make_str_prop(obj.get("visibility"))
        self.created_by = self._make_str_prop(obj.get("createdBy"))
        self.created_at = self._make_datetime_prop(obj.get("createdAt"))
        self.updated_at = self._make_datetime_prop(obj.get("updatedAt"))
        self.item_count = self._make_int_prop(obj.get("itemCount"))


class PinSet(PinSetSummary):
    """Represents a pin set, a named list of pinned STAC items in a workspace, with its item
    references.

    Args:
        client (Client): Instance of pyeodh request client
        headers (Headers): Response headers received when requesting this record
        data (Any): Raw response data received when requesting this record
    """

    def _set_props(self, obj: dict) -> None:
        super()._set_props(obj)
        self.items = [PinSetItem(self._client, self._headers, d, parent=self) for d in obj.get("items") or []]

    def load_items(self) -> list[Item]:
        """Fetch the STAC items in this pin set from their selfHrefs, in set order. The
        resource catalog checks your own access to each item, so items you can't read are
        skipped with a warning.

        Returns:
            list[Item]: The STAC items you can read.
        """
        items = []
        for ref in self.items:
            try:
                items.append(ref.load())
            except requests.HTTPError as e:
                if e.response is None or e.response.status_code not in (401, 403, 404):
                    raise
                logger.warning(f"Skipping pinned item {ref.self_href}: HTTP {e.response.status_code}")
        return items


class Workspace:
    """Contains methods for interacting with EODH workspaces."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def _resolve_workspace_name(self, workspace_name: str | None) -> str:
        """Check the client has a token and return the workspace name, defaulting to the
        client's username."""

        if self._client.token is None:
            raise ValueError("Valid token is required for accessing protected API endpoints.")

        if workspace_name is None:
            workspace_name = self._client.username
        if workspace_name is None:
            raise ValueError("Workspace name is required")
        return workspace_name

    def _pin_sets_url(self, workspace_name: str | None, *path: str) -> str:
        return join_url("/api/workspaces", self._resolve_workspace_name(workspace_name), "pin-sets", *path)

    def list_pin_sets(self, workspace_name: str | None = None) -> list[PinSetSummary]:
        """List the pin sets you can see in a workspace: every workspace-wide set, plus
        private sets you created. Workspace admins see every private set.

        Calls: GET /api/workspaces/{workspace_name}/pin-sets

        Args:
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.

        Returns:
            list[PinSetSummary]: Pin sets without their items.
        """
        headers, response = self._client._request_json("GET", self._pin_sets_url(workspace_name))
        return [PinSetSummary(self._client, headers, d) for d in response or []]

    def get_pin_set(self, set_id: str, workspace_name: str | None = None) -> PinSet:
        """Fetch a pin set with its item references. Use `PinSet.load_items` to fetch the
        STAC items.

        Calls: GET /api/workspaces/{workspace_name}/pin-sets/{set_id}

        Args:
            set_id (str): Pin set ID
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.

        Returns:
            PinSet: Initialized pin set object.
        """
        headers, response = self._client._request_json("GET", self._pin_sets_url(workspace_name, set_id))
        return PinSet(self._client, headers, response)

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

        workspace_name = self._resolve_workspace_name(workspace_name)
        url = s3_url(workspace_name, self._client.environment, ws_file_path)

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
