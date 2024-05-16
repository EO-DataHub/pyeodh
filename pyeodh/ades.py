from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Any

from pyeodh.eodh_object import EodhObject
from pyeodh.types import Headers, Link

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from pyeodh.client import Client


class AdesRelType(StrEnum):
    SELF = "self"
    PROCESSES = "http://www.opengis.net/def/rel/ogc/1.0/processes"
    JOBS = "http://www.opengis.net/def/rel/ogc/1.0/job-list"


@dataclass
class Metadata:
    title: str | None
    role: str | None
    href: str | None

    @classmethod
    def from_dict(cls, data: dict[str, str]):
        return cls(
            title=data.get("title", None),
            role=data.get("role", None),
            href=data.get("href", None),
        )


@dataclass
class Parameter:
    name: str
    value: list[Any]


@dataclass
class AdditionalParameters:

    title: str | None
    role: str | None
    href: str | None
    parameters: list[Parameter]

    @classmethod
    def from_dict(cls, data: dict):
        params = [Parameter(d["name"], d["value"]) for d in data.get("parameters", [])]
        return cls(
            title=data.get("title", None),
            role=data.get("role", None),
            href=data.get("href", None),
            parameters=params,
        )


class Process(EodhObject):

    def __init__(self, client: Client, headers: Headers, data: Any):
        super().__init__(client, headers, data)

    def _set_props(self, obj: dict) -> None:
        self.id = self._make_str_prop(obj.get("id"))
        self.title = self._make_str_prop(obj.get("title"))
        self.description = self._make_str_prop(obj.get("description"))
        self.links = [Link.from_dict(d) for d in obj.get("links", [])]
        self.version = self._make_str_prop(obj.get("version"))
        self.mutable: bool | None = obj.get("mutable")
        self.job_control_options = self._make_list_of_strs_prop(
            obj.get("jobControlOptions", [])
        )
        self.output_transmission = self._make_list_of_strs_prop(
            obj.get("outputTransmission", [])
        )
        self.keywords = self._make_list_of_strs_prop(obj.get("keywords", []))
        self.metadata: list[Metadata] = [
            Metadata.from_dict(d) for d in obj.get("metadata", [])
        ]
        self.additional_parameters: AdditionalParameters = (
            AdditionalParameters.from_dict(obj.get("additionalParameters", {}))
        )


class Ades(EodhObject):

    def __init__(self, client: Client, headers: Headers, data: Any):
        super().__init__(client, headers, data)

    def _set_props(self, obj: dict) -> None:
        self._title = self._make_str_prop(obj.get("title"))
        self.links = [Link.from_dict(d) for d in obj.get("links", [])]

    @property
    def title(self) -> str:
        if self._title is None:
            raise ValueError(f"Property title not set for {self}")
        return self._title

    @cached_property
    def self_href(self) -> str:
        ln = Link.get_link(self.links, AdesRelType.SELF)
        if ln is None:
            raise ValueError(f"{self} does not have a link pointing to self")
        return ln.href

    @cached_property
    def processes_href(self) -> str:
        ln = Link.get_link(self.links, AdesRelType.PROCESSES)
        if ln is None:
            raise ValueError(f"{self} does not have a link pointing to processes")
        return ln.href

    @cached_property
    def jobs_href(self) -> str:
        ln = Link.get_link(self.links, AdesRelType.JOBS)
        if ln is None:
            raise ValueError(f"{self} does not have a link pointing to jobs")
        return ln.href
