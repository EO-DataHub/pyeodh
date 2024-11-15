import os
import time

import dotenv
import pytest
import requests

import pyeodh
from pyeodh.ades import Ades, AdesJobStatus, Job, Process


@pytest.fixture(scope="module")
def vcr_config():
    return {"filter_headers": ["Authorization"]}


@pytest.fixture
def svc() -> Ades:
    dotenv.load_dotenv()
    username = os.getenv("ADES_USER", "figi44")
    token = os.getenv("ADES_TOKEN", "test_token")
    return pyeodh.Client(username=username, token=token).get_ades()


@pytest.mark.vcr
def test_get_ades_service(svc: Ades):
    assert (
        svc.self_href
        == f"https://test.eodatahub.org.uk/ades/{svc._client.username}/ogc-api/"
    )


@pytest.mark.vcr
def test_get_processes(svc: Ades):
    processes = svc.get_processes()
    assert isinstance(processes, list)
    assert all(isinstance(p, Process) for p in processes)


@pytest.mark.vcr
def test_get_non_existent_process(svc: Ades):
    with pytest.raises(requests.exceptions.HTTPError):
        svc.get_process("non-existent-process-id")


@pytest.mark.vcr
def test_process_execution(svc: Ades):

    try:
        svc.get_process("convert-url").delete()
    except requests.exceptions.HTTPError:
        pass

    # Deploy a process
    process = svc.deploy_process(
        cwl_url=(
            "https://raw.githubusercontent.com/EOEPCA/deployment-guide/main/"
            "deploy/samples/requests/processing/convert-url-app.cwl"
        )
    )
    assert isinstance(process, Process)
    assert process.id == "convert-url"

    # Get a signle process
    single_process = svc.get_process("convert-url")
    assert isinstance(single_process, Process)
    assert single_process.id == "convert-url"

    # Update a process
    cwl_yaml = """cwlVersion: v1.0
$namespaces:
  s: https://schema.org/
s:softwareVersion: 0.1.2
schemas:
  - http://schema.org/version/9.0/schemaorg-current-http.rdf
$graph:
  # Workflow entrypoint
  - class: Workflow
    id: convert-url
    label: updated convert url app
    doc: Updated Convert URL YAML
    requirements:
      ResourceRequirement:
        coresMax: 1
        ramMax: 1024
    inputs:
      fn:
        label: the operation to perform
        doc: the operation to perform
        type: string
      url:
        label: the image to convert
        doc: the image to convert
        type: string
      size:
        label: the percentage for a resize operation
        doc: the percentage for a resize operation
        type: string
    outputs:
      - id: converted_image
        type: Directory
        outputSource:
          - convert/results
    steps:
      convert:
        run: "#convert"
        in:
          fn: fn
          url: url
          size: size
        out:
          - results
  # convert.sh - takes input args `--url`
  - class: CommandLineTool
    id: convert
    requirements:
      ResourceRequirement:
        coresMax: 1
        ramMax: 512
    hints:
      DockerRequirement:
        dockerPull: eoepca/convert:latest
    baseCommand: convert.sh
    inputs:
      fn:
        type: string
        inputBinding:
          position: 1
      url:
        type: string
        inputBinding:
          position: 2
          prefix: --url
      size:
        type: string
        inputBinding:
          position: 3
    outputs:
      results:
        type: Directory
        outputBinding:
          glob: .
"""

    process.update(cwl_yaml=cwl_yaml)
    assert process.title == "convert url app"
    assert process.description == "Convert URL YAML"

    # Execute a process
    job = process.execute(
        {
            "fn": "resize",
            "url": "https://eoepca.org/media_portal/images/logo6_med.original.png",
            "size": "50%",
        }
    )
    assert isinstance(job, Job)
    assert job.status in [e.value for e in AdesJobStatus]
    assert job.process_id == "convert-url"

    # Refresh a job until finished
    job.refresh()
    while job.status == AdesJobStatus.RUNNING.value:
        time.sleep(2)
        job.refresh()

    # # Get result items
    # for _ in range(12):
    #     try:
    #         items = job.get_result_items()
    #         if isinstance(items, list) and all(
    #             isinstance(item, Item) for item in items
    #         ):
    #             break
    #     except ResultsNotReadyError:
    #         time.sleep(5)
    #         job.refresh()
    # else:
    #     raise AssertionError("Failed to get result items")


@pytest.mark.vcr
def test_get_jobs(svc: Ades):
    jobs = svc.get_jobs()
    assert isinstance(jobs, list)
    assert all(isinstance(job, Job) for job in jobs)


@pytest.mark.vcr
def test_get_job(svc: Ades):
    jobs = svc.get_jobs()
    if len(jobs) > 0:
        job = svc.get_job(jobs[0].id)
        assert isinstance(job, Job)
        assert job.id == jobs[0].id


@pytest.mark.vcr
def test_delete_job(svc: Ades):
    p = svc.get_process("convert-url")
    j = p.execute({})
    j.delete()
    assert j.status == AdesJobStatus.DISMISSED.value
