from __future__ import annotations
from typing import TYPE_CHECKING

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client


class ResourceCatalog:
    def __init__(self, client: Client, data) -> None:
        self._client = client
        self.data = data
