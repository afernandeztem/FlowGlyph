"""Running UiPath processes as jobs in Orchestrator, and waiting for their result.

Only a project's entry point is published as a process, so only entry-point capabilities can be
run; the other workflows of a project run inside it. The job's input arguments are the
capability's inputs and its output arguments become the result.
"""

import json
import time
from http import HTTPStatus
from typing import Any, ClassVar, cast

from flowglyph.errors import ExecutionError, OutcomeUnknownError
from flowglyph.gateway.executors._http import HttpClient
from flowglyph.gateway.executors.auth import Auth
from flowglyph.ir import Capability

_FINISHED = frozenset({"Successful", "Faulted", "Stopped", "Terminating", "Suspended"})
# States a job can still leave, or in which part of the work may yet be done.
_UNSETTLED = frozenset({"Terminating", "Suspended"})
_START_JOBS = "odata/Jobs/UiPath.Server.Configuration.OData.StartJobs"


class OrchestratorExecutor:
    """Starts jobs in the Orchestrator at `url`, inside `folder`, and waits for them."""

    name: ClassVar[str] = "uipath"

    def __init__(
        self,
        url: str,
        auth: Auth,
        *,
        folder: str,
        processes: dict[str, str] | None = None,
        timeout_seconds: float = 600.0,
        poll_seconds: float = 2.0,
    ) -> None:
        """Run processes in `folder`, naming them after the project unless `processes` maps it."""
        self.url = url.rstrip("/")
        self.auth = auth
        self.folder = folder
        self.processes = processes or {}
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds
        self.client = HttpClient(timeout_seconds=60.0)
        self._folder_id: str | None = None

    def execute(self, capability: Capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Start the process behind `capability` with `arguments` and wait until it ends.

        Raises:
            ExecutionError: If the capability is not a published process, Orchestrator refuses
                the job, or the job faults.
            OutcomeUnknownError: If the job was started and is not known to have ended: it
                did not finish in time, or Orchestrator stopped answering.
        """
        process = self._process_name(capability)
        release_key = self._release_key(process)
        started = self._post(
            _START_JOBS,
            {
                "startInfo": {
                    "ReleaseKey": release_key,
                    "Strategy": "ModernJobsCount",
                    "JobsCount": 1,
                    "InputArguments": json.dumps(arguments),
                }
            },
        )
        jobs = cast("list[dict[str, Any]]", started.get("value", []))
        if not jobs:
            raise ExecutionError(f"Orchestrator started no job for {process}")
        job_id = str(jobs[0]["Id"])
        return self._wait(job_id, process)

    def _process_name(self, capability: Capability) -> str:
        if capability.source.provider != "uipath" or not capability.entry_point:
            raise ExecutionError(
                f"{capability.id} is not a published process; only a project's entry point "
                "runs as an Orchestrator job"
            )
        project = capability.id.split("/")[1]
        return self.processes.get(project, project)

    def _release_key(self, process: str) -> str:
        releases = self._get("odata/Releases", [("$filter", f"ProcessKey eq {_quoted(process)}")])
        found = cast("list[dict[str, Any]]", releases.get("value", []))
        if not found:
            raise ExecutionError(
                f"no process named {process!r} is published in folder {self.folder!r}; "
                "map the project to its process name in the connection"
            )
        return str(found[0]["Key"])

    def _wait(self, job_id: str, process: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                job = self._get(f"odata/Jobs({job_id})")
            except ExecutionError as error:
                raise OutcomeUnknownError(
                    f"job {job_id} of {process} was started and can no longer be followed: {error}"
                ) from error
            state = str(job.get("State", ""))
            if state in _FINISHED:
                break
            if time.monotonic() >= deadline:
                raise OutcomeUnknownError(
                    f"job {job_id} of {process} is still {state or 'pending'} after "
                    f"{self.timeout_seconds:.0f}s"
                )
            time.sleep(self.poll_seconds)
        if state in _UNSETTLED:
            raise OutcomeUnknownError(f"job {job_id} of {process} is {state}, not finished")
        if state != "Successful":
            detail = str(job.get("Info") or "no details")
            raise ExecutionError(f"job {job_id} of {process} ended {state}: {detail}")
        outputs: Any = job.get("OutputArguments") or "{}"
        parsed: Any = json.loads(outputs) if isinstance(outputs, str) else outputs
        return {
            "job_id": job_id,
            "state": state,
            "outputs": parsed if isinstance(parsed, dict) else {"value": parsed},
        }

    def _headers(self) -> dict[str, str]:
        if self._folder_id is None:
            self._folder_id = self._find_folder()
        return {
            "X-UIPATH-OrganizationUnitId": self._folder_id,
            **self.auth.headers(self.client),
        }

    def _find_folder(self) -> str:
        response = self.client.request(
            "GET",
            f"{self.url}/odata/Folders",
            headers=self.auth.headers(self.client),
            query=[("$filter", f"FullyQualifiedName eq {_quoted(self.folder)}")],
        )
        found = cast(
            "list[dict[str, Any]]", _payload(response.json(), response.status).get("value", [])
        )
        if not found:
            raise ExecutionError(f"no folder named {self.folder!r} in {self.url}")
        return str(found[0]["Id"])

    def _get(self, path: str, query: list[tuple[str, str]] | None = None) -> dict[str, Any]:
        response = self.client.request(
            "GET", f"{self.url}/{path}", headers=self._headers(), query=query or []
        )
        return _payload(response.json(), response.status)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.client.request(
            "POST", f"{self.url}/{path}", headers=self._headers(), json_body=body
        )
        return _payload(response.json(), response.status)


def _quoted(text: str) -> str:
    """`text` as an OData string literal; a quote inside it is doubled, so it stays one value."""
    return "'" + text.replace("'", "''") + "'"


def _payload(answer: Any, status: int) -> dict[str, Any]:
    data: dict[str, Any] = cast("dict[str, Any]", answer) if isinstance(answer, dict) else {}
    if status >= HTTPStatus.BAD_REQUEST:
        detail = str(cast("object", data.get("message")) or cast("object", answer) or "no details")
        raise ExecutionError(f"Orchestrator answered {status}: {detail}")
    return data
