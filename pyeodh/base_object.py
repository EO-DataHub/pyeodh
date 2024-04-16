from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client


class BaseObject:
    """Base class for other classes representing objects returned by EODH APIs."""

    def __init__(
        self,
        client: Client,
        headers: dict,
        data: Any,
    ):
        self._client = client
        self._headers = headers
        self._raw_data = data

        self._set_properties()

    def _set_properties(self) -> None:
        raise NotImplementedError(
            f"Method _set_properties not implemented in {self.__class__.__name__}."
        )
