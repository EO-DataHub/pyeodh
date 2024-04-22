from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type
import typing

from pyeodh.types import Headers

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client


T = typing.TypeVar("T")


class BaseObject:
    """Base class for other classes representing objects returned by EODH APIs."""

    def __init__(
        self,
        client: Client,
        headers: Headers,
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

    @staticmethod
    def _make_prop(value: T, t: Type[T]) -> T:
        if value is None or isinstance(value, t):
            return value
        else:
            raise TypeError(f"Expected {t}, received {value.__class__}.")

    @staticmethod
    def _make_list_of_type_prop(value: list[T], t: Type[T]) -> list[T]:
        if not isinstance(value, list):
            raise TypeError(f"Expected list of {t}, received {value.__class__}.")
        if not all(isinstance(x, t) for x in value):
            raise TypeError(
                (
                    f"Expected list of {t}, received list of "
                    f"{next(iter(value), None).__class__}."
                )
            )
        else:
            return value

    @staticmethod
    def _make_str_prop(value: str | None) -> str | None:
        return BaseObject._make_prop(value, str)

    @staticmethod
    def _make_int_prop(value: int | None) -> int | None:
        return BaseObject._make_prop(value, int)

    @staticmethod
    def _make_dict_prop(value: dict[str, Any]) -> dict[str, Any]:
        return BaseObject._make_prop(value, dict)

    @staticmethod
    def _make_list_of_dicts_prop(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return BaseObject._make_list_of_type_prop(value, dict)

    @staticmethod
    def _make_list_of_strs_prop(value: list[str]) -> list[str]:
        return BaseObject._make_list_of_type_prop(value, str)
