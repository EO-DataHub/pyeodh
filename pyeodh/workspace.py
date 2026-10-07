from __future__ import annotations

import copy
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Union

import pystac
import requests

from pyeodh.eodh_object import EodhObject
from pyeodh.resource_catalog import Item
from pyeodh.utils import join_url, remove_null_items, s3_url

if TYPE_CHECKING:
    from pyeodh.client import Client
    from pyeodh.types import Headers

logger = logging.getLogger(__name__)

PinSetVisibility = Literal["workspace", "private"]


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

    def to_dict(self) -> dict[str, Any]:
        """Return this item reference as received from the API."""
        return copy.deepcopy(self._raw_data)

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

    def to_dict(self) -> dict[str, Any]:
        """Return this pin set as received from the API."""
        return copy.deepcopy(self._raw_data)


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
        skipped with a warning. Use `pystac.Item.from_dict(item.to_dict())` if you need
        pystac Items.

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


PinSetItemLike = Union[Item, pystac.Item, PinSetItem, dict[str, Any]]
"""A STAC item, an existing pin set item, or a reference dict with `collectionId`,
`itemId` and `selfHref` keys."""


def _to_item_ref(item: PinSetItemLike) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if isinstance(item, PinSetItem):
        return remove_null_items(
            {
                "collectionId": item.collection_id,
                "itemId": item.item_id,
                "selfHref": item.self_href,
                "display": item.display,
            }
        )
    if isinstance(item, Item):
        item = item._pystac_object
    self_href = item.get_self_href()
    if item.collection_id is None or self_href is None:
        raise ValueError(f"Item {item.id} needs a collection and a self link to be pinned")
    return {"collectionId": item.collection_id, "itemId": item.id, "selfHref": self_href}


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

    def create_pin_set(
        self,
        name: str,
        description: str = "",
        visibility: PinSetVisibility = "workspace",
        items: Iterable[PinSetItemLike] | None = None,
        workspace_name: str | None = None,
    ) -> PinSet:
        """Create a pin set. Any workspace member can create one. Items repeated in `items`
        (same selfHref) are kept once.

        Calls: POST /api/workspaces/{workspace_name}/pin-sets

        Args:
            name (str): Name of the pin set, unique within the workspace
            description (str, optional): Description of the pin set. Defaults to "".
            visibility (PinSetVisibility, optional): "workspace" to share the set with
                every workspace member, or "private" to keep it to yourself and workspace
                admins. Defaults to "workspace".
            items (Iterable[PinSetItemLike] | None, optional): Items to pin. Each selfHref
                must be on the platform resource catalog. Defaults to None.
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.

        Returns:
            PinSet: The created pin set.
        """
        url = self._pin_sets_url(workspace_name)
        data = {
            "name": name,
            "description": description,
            "visibility": visibility,
            "items": [_to_item_ref(i) for i in items or []],
        }
        headers, response = self._client._request_json("POST", url, data=data)
        return PinSet(self._client, headers, response)

    def update_pin_set(
        self,
        set_id: str,
        name: str | None = None,
        description: str | None = None,
        visibility: PinSetVisibility | None = None,
        workspace_name: str | None = None,
    ) -> PinSet:
        """Change a pin set's name, description or visibility. Only provide the values you
        want to change. Only the set's creator or a workspace admin can do this.

        Calls: PATCH /api/workspaces/{workspace_name}/pin-sets/{set_id}

        Args:
            set_id (str): Pin set ID
            name (str | None, optional): New name. Defaults to None.
            description (str | None, optional): New description. Defaults to None.
            visibility (PinSetVisibility | None, optional): New visibility. Defaults to
                None.
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.

        Returns:
            PinSet: The updated pin set.
        """
        data = remove_null_items({"name": name, "description": description, "visibility": visibility})
        if not data:
            raise ValueError("Provide at least one of name, description or visibility.")
        url = self._pin_sets_url(workspace_name, set_id)
        headers, response = self._client._request_json("PATCH", url, data=data)
        return PinSet(self._client, headers, response)

    def delete_pin_set(self, set_id: str, workspace_name: str | None = None) -> None:
        """Delete a pin set and its items. Only the set's creator or a workspace admin can
        do this.

        Calls: DELETE /api/workspaces/{workspace_name}/pin-sets/{set_id}

        Args:
            set_id (str): Pin set ID
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.
        """
        self._client._request_raw("DELETE", self._pin_sets_url(workspace_name, set_id))

    def replace_pin_set_items(
        self,
        set_id: str,
        items: Iterable[PinSetItemLike],
        workspace_name: str | None = None,
    ) -> PinSet:
        """Replace every item in a pin set. Pass an empty list to clear it. Only the set's
        creator or a workspace admin can do this.

        Calls: PUT /api/workspaces/{workspace_name}/pin-sets/{set_id}/items

        Args:
            set_id (str): Pin set ID
            items (Iterable[PinSetItemLike]): Items to pin. Each selfHref must be on the
                platform resource catalog.
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.

        Returns:
            PinSet: The updated pin set.
        """
        url = self._pin_sets_url(workspace_name, set_id, "items")
        data = {"items": [_to_item_ref(i) for i in items]}
        headers, response = self._client._request_json("PUT", url, data=data)
        return PinSet(self._client, headers, response)

    def add_pin_set_items(
        self,
        set_id: str,
        items: Iterable[PinSetItemLike],
        workspace_name: str | None = None,
    ) -> PinSet:
        """Add items to the end of a pin set. Items already in the set (same selfHref) are
        skipped. Only the set's creator or a workspace admin can do this.

        Calls: POST /api/workspaces/{workspace_name}/pin-sets/{set_id}/items

        Args:
            set_id (str): Pin set ID
            items (Iterable[PinSetItemLike]): Items to pin. Each selfHref must be on the
                platform resource catalog.
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.

        Returns:
            PinSet: The updated pin set.
        """
        url = self._pin_sets_url(workspace_name, set_id, "items")
        data = {"items": [_to_item_ref(i) for i in items]}
        headers, response = self._client._request_json("POST", url, data=data)
        return PinSet(self._client, headers, response)

    def remove_pin_set_item(self, set_id: str, entry_id: str, workspace_name: str | None = None) -> None:
        """Remove one item from a pin set. Only the set's creator or a workspace admin can
        do this.

        Calls: DELETE /api/workspaces/{workspace_name}/pin-sets/{set_id}/items/{entry_id}

        Args:
            set_id (str): Pin set ID
            entry_id (str): ID of the item's entry in the set, `PinSetItem.id`
            workspace_name (str, optional): Name of the workspace. Defaults to the username
                pyeodh client was initialized with.
        """
        self._client._request_raw("DELETE", self._pin_sets_url(workspace_name, set_id, "items", entry_id))

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
