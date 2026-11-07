"""`flowglyph.connections.yaml`: which system runs which capabilities, and how to reach it.

The file holds addresses and the names of the environment variables that hold secrets, never
the secrets themselves, so it can be committed next to the catalog.

```yaml
connections:
  payments:
    type: http
    base_url: https://api.example.com/v1
    auth: {type: bearer, token_env: PAYMENTS_TOKEN}
    capabilities: ["openapi/Payments_API/*"]
  erp:
    type: odata
    service_url: https://erp.example.com/sap/opu/odata/sap/ZSUPPLIER_INVOICE_SRV
    auth: {type: basic, user_env: SAP_USER, password_env: SAP_PASSWORD}
    capabilities: ["sap/ZSUPPLIER_INVOICE_SRV/*"]
  robots:
    type: uipath
    url: https://cloud.uipath.com/acme/finance/orchestrator_
    folder: Finance/Invoices
    auth:
      type: client_credentials
      token_url: https://cloud.uipath.com/identity_/connect/token
      client_id_env: UIPATH_CLIENT_ID
      client_secret_env: UIPATH_CLIENT_SECRET
      scope: OR.Folders.Read OR.Execution OR.Jobs
    capabilities: ["uipath/*"]
```
"""

from fnmatch import fnmatchcase
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from flowglyph.errors import ExecutionError
from flowglyph.gateway.executors.auth import Auth, NoAuth
from flowglyph.gateway.executors.http import HttpExecutor
from flowglyph.gateway.executors.odata import ODataExecutor
from flowglyph.gateway.executors.orchestrator import OrchestratorExecutor
from flowglyph.ir import Capability

CONNECTIONS_FILE = "flowglyph.connections.yaml"


class _Connection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    capabilities: tuple[str, ...] = Field(min_length=1)
    auth: Auth = NoAuth()
    timeout_seconds: float = Field(default=60.0, gt=0)

    def matches(self, capability_id: str) -> bool:
        """Whether this connection runs the capability with `capability_id`."""
        return any(fnmatchcase(capability_id, pattern) for pattern in self.capabilities)


class HttpConnection(_Connection):
    """An HTTP API described by an OpenAPI document."""

    type: Literal["http"]
    base_url: str

    def executor(self) -> HttpExecutor:
        """The executor for this API."""
        return HttpExecutor(self.base_url, self.auth, timeout_seconds=self.timeout_seconds)


class ODataConnection(_Connection):
    """An SAP OData service, V2 or V4."""

    type: Literal["odata"]
    service_url: str

    def executor(self) -> ODataExecutor:
        """The executor for this service."""
        return ODataExecutor(self.service_url, self.auth, timeout_seconds=self.timeout_seconds)


class UiPathConnection(_Connection):
    """A UiPath Orchestrator tenant and the folder its processes live in."""

    type: Literal["uipath"]
    url: str
    folder: str
    processes: dict[str, str] = {}
    timeout_seconds: float = Field(default=600.0, gt=0)
    poll_seconds: float = Field(default=2.0, gt=0)

    def executor(self) -> OrchestratorExecutor:
        """The executor for this Orchestrator."""
        return OrchestratorExecutor(
            self.url,
            self.auth,
            folder=self.folder,
            processes=self.processes,
            timeout_seconds=self.timeout_seconds,
            poll_seconds=self.poll_seconds,
        )


type Connection = Annotated[
    HttpConnection | ODataConnection | UiPathConnection, Field(discriminator="type")
]


class Connections(BaseModel):
    """Every system the gateway can run capabilities against."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    connections: dict[str, Connection]

    @classmethod
    def load(cls, path: str | Path) -> "Connections":
        """Read a connections file.

        Raises:
            ExecutionError: If the file is missing or does not describe connections.
        """
        file = Path(path)
        if not file.is_file():
            raise ExecutionError(f"{file} does not exist")
        document: object = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        try:
            return cls.model_validate(document)
        except ValidationError as error:
            raise ExecutionError(f"{file} is not a valid connections file: {error}") from error

    def variables(self) -> dict[str, list[str]]:
        """Per connection, the environment variables its credentials need."""
        return {name: connection.auth.variables() for name, connection in self.connections.items()}

    def for_capability(self, capability_id: str) -> tuple[str, Connection] | None:
        """The first connection whose patterns match `capability_id`."""
        for name, connection in self.connections.items():
            if connection.matches(capability_id):
                return name, connection
        return None


class ConnectedExecutor:
    """Routes each capability to the connection that runs it, by capability id pattern."""

    name: ClassVar[str] = "connected"

    def __init__(self, connections: Connections) -> None:
        """Run capabilities through `connections`."""
        self.connections = connections
        self._executors: dict[str, Any] = {}

    def execute(self, capability: Capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run `capability` on its connection.

        Raises:
            ExecutionError: If no connection runs it, or the run fails.
        """
        found = self.connections.for_capability(capability.id)
        if found is None:
            raise ExecutionError(
                f"no connection runs {capability.id}; add one to {CONNECTIONS_FILE}, or serve "
                "without --connections to dry-run it"
            )
        name, connection = found
        if name not in self._executors:
            self._executors[name] = connection.executor()
        output = cast("dict[str, Any]", self._executors[name].execute(capability, arguments))
        return {"connection": name, **output}
