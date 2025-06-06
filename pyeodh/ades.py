from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime as Datetime
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any

from pyeodh import consts
from pyeodh.eodh_object import EodhObject
from pyeodh.pagination import PaginatedList
from pyeodh.resource_catalog import Collection, Item
from pyeodh.types import Headers, Link
from pyeodh.utils import join_url

if TYPE_CHECKING:
    # avoids conflicts since there are also kwargs and attrs called `datetime`
    from pyeodh.client import Client

logger = logging.getLogger(__name__)


class AdesRelType(Enum):
    SELF = "self"
    STATUS = "monitor"
    PROCESSES = "http://www.opengis.net/def/rel/ogc/1.0/processes"
    JOBS = "http://www.opengis.net/def/rel/ogc/1.0/job-list"
    RESULTS = "http://www.opengis.net/def/rel/ogc/1.0/results"
    RESULTS_NOT_READY = (
        "http://www.opengis.net/def/rel/ogc/1.0/exception/result-not-ready"
    )
    EXECUTE = "http://www.opengis.net/def/rel/ogc/1.0/execute"


class AdesJobStatus(Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    DISMISSED = "dismissed"


class ResultsNotReadyError(Exception):
    """Exception raised when job results are not ready."""

    pass


class Job(EodhObject):
    """Represents ADES Job record.

    Args:
        client (Client): Instance of pyeodh request client
        headers (Headers): Response headers received when requesting this record
        data (Any): Raw response data received when requesting this record
    """

    def __init__(self, client: Client, headers: Headers, data: Any, **kwargs):
        super().__init__(client, headers, data, **kwargs)

    def _set_props(self, obj: dict) -> None:
        self.id = self._make_str_prop(obj.get("jobID"))
        self.process_id = self._make_str_prop(obj.get("processID"))
        self.type = self._make_str_prop(obj.get("type"))
        self.status = self._make_str_prop(obj.get("status"))
        self.message = self._make_str_prop(obj.get("message"))
        self.progress = self._make_int_prop(obj.get("progress"))
        self.links = [Link.from_dict(d) for d in obj.get("links", [])]
        if "created" in obj:
            created: str = obj.get("created", "")
            self.created = Datetime.fromisoformat(created.replace("Z", "+00:00"))
        if "started" in obj:
            started: str = obj.get("started", "'")
            self.started = Datetime.fromisoformat(started.replace("Z", "+00:00"))
        if "finished" in obj:
            finished: str = obj.get("finished", "")
            self.finished = Datetime.fromisoformat(finished.replace("Z", "+00:00"))
        if "updated" in obj:
            updated: str = obj.get("updated", "")
            self.updated = Datetime.fromisoformat(updated.replace("Z", "+00:00"))

    @cached_property
    def self_href(self) -> str:
        """URL of this object."""
        ln = Link.get_link(self.links, AdesRelType.STATUS.value)
        if ln is None:
            raise ValueError(f"{self} does not have a link pointing to self")
        return ln.href

    def refresh(self) -> None:
        """Refresh this object with the latest data from the API."""
        headers, response = self._client._request_json("GET", self.self_href)
        if response:
            self._set_props(response)

    def delete(self) -> None:
        """Stop and delete this job."""
        headers, response = self._client._request_json("DELETE", self.self_href)
        if response:
            self._set_props(response)

    def _get_results_collection(self) -> Collection | None:
        ln = Link.get_link(self.links, AdesRelType.RESULTS.value)
        if self.status != AdesJobStatus.SUCCESSFUL.value:
            raise ResultsNotReadyError(
                f"Results are only available for successful jobs, "
                f"job {self.id} is {self.status}"
            )
        if ln is None:
            raise ResultsNotReadyError(
                f"Job {self.id} does not yet have a link to results."
            )
        headers, response = self._client._request_json("GET", ln.href)
        if (
            response.get("type", AdesRelType.RESULTS_NOT_READY.value)
            == AdesRelType.RESULTS_NOT_READY.value
        ):

            logger.info(f"Job {self.id} results not ready.")
            raise ResultsNotReadyError(f"Job {self.id} results not ready.")

        return Collection(self._client, headers, response)

    def get_result_items(self) -> list[Item]:
        """Get job outputs

        Returns:
            list[Item]: List of items generated by job
        """
        collection = self._get_results_collection()
        if not collection:
            return []
        links = collection._pystac_object.get_item_links()
        items = []
        for link in links:
            href = link._target_href
            if not href:
                continue
            headers, response = self._client._request_json(
                "GET",
                href,
                headers=Headers({"Authorization": f"Bearer {self._client.token}"}),
            )
            items.append(Item(self._client, headers, response))
        return items


@dataclass
class Metadata:
    """Represents process metadata object."""

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
    """Represents a single process parameter."""

    name: str
    value: list[Any]


@dataclass
class AdditionalParameters:
    """Represents additional parameters of the process."""

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
    """Represents ADES Process record.

    Args:
        client (Client): Instance of pyeodh request client
        headers (Headers): Response headers received when requesting this record
        data (Any): Raw response data received when requesting this record
        parent_url (str): URL of the parent API endpoint, usually `/processes`
    """

    def __init__(self, client: Client, headers: Headers, data: Any, parent_url: str):
        super().__init__(client, headers, data)
        self.self_href = join_url(parent_url, self.id or "")

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
        self.inputs_schema = self._make_dict_prop(obj.get("inputs", {}))
        self.outputs_schema = self._make_dict_prop(obj.get("outputs", {}))

    @cached_property
    def execute_href(self) -> str:
        """URL pointing to processes execution endpoint."""

        return join_url(self.self_href, "execution")

    def execute(self, inputs: dict, workspace: str | None = None) -> Job:
        """Trigger process workflow execution.

        Calls: POST /processes/{process_id}/execution

        Args:
            inputs (dict): A dictionary containing inputs structured according to
                schema defined by the process.

        Returns:
            Job: Object representing the triggered job.
        """

        # TODO: handle inputs, validate against the schema
        if inputs.get("workspace") is None:
            inputs["workspace"] = workspace or self._client.username

        post_headers = Headers()
        post_headers["Prefer"] = "respond-async"
        post_data = {"inputs": inputs}
        headers, response = self._client._request_json(
            "POST", self.execute_href, headers=post_headers, data=post_data
        )
        return Job(self._client, headers, response)

    def update(
        self,
        cwl_url: str | None = None,
        cwl_yaml: str | None = None,
    ) -> None:
        """Update the process workflow. `cwl_url` and `cwl_yaml` parameters are
        mutually exclusive.

        Calls: PUT /processes/{process_id}

        Args:
            cwl_url (str | None, optional): URL pointing to the workflow CWL file.
                Defaults to None.
            cwl_yaml (str | None, optional): Content of the CWL file in yaml format.
                Defaults to None.
        """

        def encode(data: str) -> tuple[str, str]:
            return "application/cwl+yaml", data

        if cwl_yaml is not None and cwl_url is not None:
            raise ValueError("cwl_url and cwl_yaml arguments are mutually exclusive.")
        if cwl_yaml is None and cwl_url is None:
            raise ValueError("Provide either cwl_yaml or cwl_url argument.")

        if cwl_yaml is not None:
            headers, response = self._client._request_json(
                "PUT", self.self_href, data=cwl_yaml, encode=encode
            )

        if cwl_url is not None:
            data = {
                "executionUnit": {
                    "href": cwl_url,
                    "type": "application/cwl",
                }
            }
            headers, response = self._client._request_json(
                "PUT", self.self_href, data=data
            )

        headers, response = self._client._request_json("GET", self.self_href)
        if response:
            self._set_props(response)

    def delete(self) -> None:
        """Delete this record."""
        self._client._request_raw("DELETE", self.self_href)


class Ades(EodhObject):
    """Represents ADES API service.

    Args:
        client (Client): Instance of pyeodh request client
        headers (Headers): Response headers received when requesting this record
        data (Any): Raw response data received when requesting this record
    """

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
        """URL of this record."""
        ln = Link.get_link(self.links, AdesRelType.SELF.value)
        if ln is None:
            raise ValueError(f"{self} does not have a link pointing to self")
        return ln.href

    @cached_property
    def processes_href(self) -> str:
        """URL pointing to processes endpoint."""
        return join_url(self.self_href, "processes")

    @cached_property
    def jobs_href(self) -> str:
        """URL pointing to jobs endpoint."""
        return join_url(self.self_href, "jobs")

    def get_processes(self) -> list[Process]:
        """Fetches available processes

        Calls: GET /processes

        Returns:
            list[Process]: List of available processes.
        """

        headers, response = self._client._request_json("GET", self.processes_href)
        if not response:
            return []
        return [
            Process(self._client, headers, item, self.processes_href)
            for item in response.get("processes", [])
        ]

    def get_process(self, process_id: str) -> Process:
        """Fetch an individual process

        Calls: GET /processes/{process_id}

        Args:
            process_id (str): Process ID

        Returns:
            Process: Initialized process object.
        """

        url = join_url(self.processes_href, process_id)
        headers, response = self._client._request_json("GET", url)
        return Process(self._client, headers, response, self.processes_href)

    def deploy_process(
        self,
        cwl_url: str | None = None,
        cwl_yaml: str | None = None,
    ) -> Process:
        """Deploy a process.

        Calls: POST /processes

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
        headers = None
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

        location = headers.get("Location") if headers else None
        if not location:
            raise RuntimeError("Did not receive location of deployed process.")

        headers, response = self._client._request_json("GET", location)
        return Process(self._client, headers, response, self.processes_href)

    def get_jobs(self, limit: int = consts.PAGINATION_LIMIT) -> PaginatedList[Job]:
        """Fetches a list of jobs triggered by the user.

        Calls: GET /jobs

        Returns:
            PaginatedList[Job]: List of user's jobs.
        """

        return PaginatedList(
            Job,
            self._client,
            "GET",
            self.jobs_href,
            "jobs",
            params={"limit": limit},
        )

    def get_job(self, job_id) -> Job:
        """Fetches an individual job.

        Args:
            job_id (_type_): Job ID.

        Returns:
            Job: Initialized job object.
        """
        url = join_url(self.jobs_href, job_id)
        headers, response = self._client._request_json("GET", url)
        return Job(self._client, headers, response)
