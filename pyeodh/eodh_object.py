from __future__ import annotations

import json
import typing
from types import NoneType
from typing import TYPE_CHECKING, Any, Literal, Type, TypeVar

from pystac import STACObject

# Avoid circular imports only for type checking
if TYPE_CHECKING:
    from pyeodh.client import Client
    from pyeodh.types import Headers


T = TypeVar("T")

T_base = TypeVar("T_base", bound="EodhObject")


def is_optional(value: Any, type: Type | tuple[Type, ...]) -> bool:
    types = ()
    if isinstance(type, tuple):
        types = (*type, NoneType)
    else:
        types = (type, NoneType)
    return isinstance(value, types)


class EodhObject:
    """Base class for other classes representing objects returned by EODH APIs."""

    def __init__(
        self,
        client: Client,
        headers: Headers,
        data: Any,
        pystac_cls: Type[STACObject] | None = None,
        **kwargs,
    ):
        self._client = client
        self._headers = headers
        self._raw_data = data
        self._parent: EodhObject | None = kwargs.get("parent")

        if pystac_cls is not None:
            self._pystac_object = pystac_cls.from_dict(data)
            self._set_props(self._pystac_object)
        else:
            self._set_props(data)

    def _set_props(self, obj) -> None:
        raise NotImplementedError(
            f"Method _set_props not implemented in {self.__class__.__name__}."
        )

    def check_conforms_to(self, conformance_uri):
        raise NotImplementedError(
            f"Method check_conforms_to not implemented in {self.__class__.__name__}."
        )

    def get_root(self) -> EodhObject:
        current = self
        while current._parent is not None:
            current = current._parent
        return current

    def to_dict(self) -> dict[str, Any]:
        if self._pystac_object:
            return self._pystac_object.to_dict()
        else:
            return self.__dict__

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
        return EodhObject._make_prop(value, str)

    @staticmethod
    def _make_int_prop(value: int | None) -> int | None:
        return EodhObject._make_prop(value, int)

    @staticmethod
    def _make_float_prop(value: float | None) -> float | None:
        return EodhObject._make_prop(value, float)

    @staticmethod
    def _make_dict_prop(value: dict[str, Any]) -> dict[str, Any]:
        return EodhObject._make_prop(value, dict)

    @staticmethod
    def _make_list_of_dicts_prop(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return EodhObject._make_list_of_type_prop(value, dict)

    @staticmethod
    def _make_list_of_strs_prop(value: list[str]) -> list[str]:
        return EodhObject._make_list_of_type_prop(value, str)

    @staticmethod
    def _make_list_of_floats_prop(value: list[float]) -> list[float]:
        return EodhObject._make_list_of_type_prop(value, float)

    def _make_class_prop(self, cls: Type[T_base], data: dict) -> T_base | None:
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

    @staticmethod
    def _make_query_dict(
        value: dict[str, Any] | list[str] | None,
    ) -> dict[str, Any] | None:
        operators = {
            ">=": "gte",
            "<=": "lte",
            "=": "eq",
            "<>": "neq",
            ">": "gt",
            "<": "lt",
        }

        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if not isinstance(value, list):
            raise Exception("Query must be a dict or list[str]")

        query = {}
        for item in value:
            if not isinstance(item, str):
                raise Exception("Query must be a dict or list[str]")

            try:
                query = query | json.loads(item)
            except json.JSONDecodeError:
                for op, op_text in operators.items():
                    parts = item.split(op)
                    if len(parts) == 2:
                        key = parts[0]
                        val = parts[1]
                        query = query | {key: {op_text: val}}
                        break
        return query

    @staticmethod
    def _format_intersects(value):
        if hasattr(value, "__geo_interface__"):
            return getattr(value, "__geo_interface__")
        return value

    @classmethod
    def from_href(cls, client: Client, href: str) -> EodhObject:
        """Fetch and initialize an object from given URL.

        Args:
            client (Client): Client instance.
            href (str): URL to fetch the object from.

        Returns:
            EodhObject: Initialized object.
        """

        headers, data = client._request_json("GET", href)
        return cls(client, headers, data)
