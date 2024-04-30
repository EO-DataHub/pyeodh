from __future__ import annotations

import typing
from types import NoneType
from typing import TYPE_CHECKING, Any, Literal, Type, TypeVar

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client
    from pyeodh.types import Headers


T = TypeVar("T")

T_base = TypeVar("T_base", bound="BaseObject")


def is_optional(value: Any, type: Type) -> bool:
    return isinstance(value, (type, NoneType))


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
        if value is None:
            return value
        if typing.get_origin(t) is Literal and value in typing.get_args(t):
            return value
        if isinstance(value, t):
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
    def _make_float_prop(value: float | None) -> float | None:
        return BaseObject._make_prop(value, float)

    @staticmethod
    def _make_dict_prop(value: dict[str, Any]) -> dict[str, Any]:
        return BaseObject._make_prop(value, dict)

    @staticmethod
    def _make_list_of_dicts_prop(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return BaseObject._make_list_of_type_prop(value, dict)

    @staticmethod
    def _make_list_of_strs_prop(value: list[str]) -> list[str]:
        return BaseObject._make_list_of_type_prop(value, str)

    @staticmethod
    def _make_list_of_floats_prop(value: list[float]) -> list[float]:
        return BaseObject._make_list_of_type_prop(value, float)

    def _make_class_prop(self, cls: Type[T_base], data: dict) -> T_base:
        if data is None:
            return None
        if isinstance(data, dict):
            return cls(self._client, self._headers, data)
        else:
            raise TypeError(f"Expected {type({})}, received {data.__class__}.")

    def _make_list_of_classes_prop(
        self, cls: Type[T_base], value: list[dict]
    ) -> list[T_base]:
        if not isinstance(value, list):
            raise TypeError(f"Expected list of dicts, received {value.__class__}.")
        if not all(isinstance(x, dict) for x in value):
            raise TypeError(
                (
                    f"Expected list of dicts, received list of "
                    f"{next(iter(value), None).__class__}."
                )
            )
        else:
            return [cls(self._client, self._headers, item) for item in value]
