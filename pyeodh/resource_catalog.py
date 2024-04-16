from __future__ import annotations

from typing import TYPE_CHECKING

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client


# TODO create Collection model
class Collection:
    pass


class ResourceCatalog:
    def __init__(self, client: Client, data) -> None:
        self._client = client
        self._data = data

    @property
    def collections(self):
        links = self._data.get("links")
        collections = [link for link in links if link.get("rel") == "child"]
        return collections

    def get_collection(self, collection):
        _, response = self._client._request_json("GET", collection.get("href"))
        return response
