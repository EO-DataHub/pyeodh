from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as Datetime
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Any

from pyeodh.eodh_object import EodhObject
from pyeodh.types import Headers, Link
from pyeodh.utils import join_url

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from pyeodh.client import Client


class AdesRelType(StrEnum):
    SELF = "self"
    PROCESSES = "http://www.opengis.net/def/rel/ogc/1.0/processes"
    JOBS = "http://www.opengis.net/def/rel/ogc/1.0/job-list"


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

    def refresh(self) -> None:
        headers, response = self._client._request_json("GET", self.self_href)
        if response:
            self._set_props(response)

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self.self_href)


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
        self.inputs_schema = self._make_dict_prop(obj.get("inputs"), {})
        self.outputs_schema = self._make_dict_prop(obj.get("outputs", {}))

    @cached_property
    def self_href(self) -> str:
        ln = Link.get_link(self.links, AdesRelType.SELF)
        if ln is None:
            raise ValueError(f"{self} does not have a link pointing to self")
        return ln.href

    def execute(self, inputs: dict) -> Job:
        headers, response = self._client._request_json(
            "POST", self.self_href, data=inputs
        )
        return Job(self._client, headers, response)

    def delete(self) -> None:
        self._client._request_json_raw("DELETE", self.self_href)

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

    def deploy_process(
        self,
        cwl_url: str | None = None,
        cwl_yaml: str | None = None,
    ) -> Process:
        """Deploy a process.

        Args:
            cwl_url (str | None, optional): Location of the cwl workflow file. Mutually
                exclusive with `cwl_yaml` arg. Defaults to None.
            cwl_yaml (str | None, optional): CWL workflow in yaml format. Mutually
                exclusive with cwl_url. Defaults to None.

        Returns:
            Process: The newly created process as returned by the API.
        """

        def encode(data: str) -> tuple[str, str]:
            return "application/cwl+yaml", data

        if cwl_yaml is not None and cwl_url is not None:
            raise ValueError("cwl_url and cwl_yaml arguments are mutually exclusive.")
        if cwl_yaml is None and cwl_url is None:
            raise ValueError("Provide either cwl_yaml or cwl_url argument.")

        if cwl_yaml is not None:
            headers, response = self._client._request_json(
                "POST", self.processes_href, data=cwl_yaml, encode=encode
            )

        if cwl_url is not None:
            data = {
                "executionUnit": {
                    "href": cwl_url,
                    "type": "application/cwl",
                }
            }
            headers, response = self._client._request_json(
                "POST", self.processes_href, data=data
            )
        location = headers.get("Location")
        if not location:
            raise RuntimeError("Did not receive location of deployed process.")

        headers, response = self._client._request_json("GET", location)
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
