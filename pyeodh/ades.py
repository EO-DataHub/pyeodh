from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Any

from pyeodh.eodh_object import EodhObject
from pyeodh.types import Headers, Link
from datetime import datetime as Datetime

from pyeodh.utils import join_url

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from pyeodh.client import Client


class Job(EodhObject):

    def __init__(self, client: Client, headers: Headers, data: Any):
        super().__init__(client, headers, data)

    def _set_props(self, obj: dict) -> None:
        self.id = self._make_str_prop(obj.get("jobID"))
        self.process_id = self._make_str_prop(obj.get("processID"))
        self.type = self._make_str_prop(obj.get("type"))
        self.status = self._make_str_prop(obj.get("status"))
        self.message = self._make_str_prop(obj.get("message"))
        self.progress = self._make_int_prop(obj.get("progress"))
        self.links = [Link.from_dict(d) for d in obj.get("links", [])]
        if "created" in obj:
            self.created = Datetime.fromisoformat(obj.get("created"))
        if "started" in obj:
            self.started = Datetime.fromisoformat(obj.get("started"))
        if "finished" in obj:
            self.finished = Datetime.fromisoformat(obj.get("finished"))
        if "updated" in obj:
            self.updated = Datetime.fromisoformat(obj.get("updated"))


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

    def get_processes(self) -> list[Process]:
        headers, response = self._client._request_json("GET", self.processes_href)
        if not response:
            return []
        return [
            Process(self._client, headers, item)
            for item in response.get("processes", [])
        ]

    def get_process(self, process_id) -> Process:
        url = join_url(self.processes_href, process_id)
        headers, response = self._client._request_json("GET", url)
        return Process(self._client, headers, response)


    def get_jobs(self) -> list[Job]:
        headers, response = self._client._request_json("GET", self.jobs_href)
        if not response:
            return []
        return [Job(self._client, headers, item) for item in response.get("jobs", [])]

    def get_job(self, job_id) -> Job:
        url = join_url(self.processes_href, job_id)
        headers, response = self._client._request_json("GET", url)
        return Job(self._client, headers, response)
