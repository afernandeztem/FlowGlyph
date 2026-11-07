"""How executors authenticate. Secrets are read from environment variables, never from files.

A connections file names the variables (`token_env: ERP_TOKEN`) so it can be committed and
reviewed without exposing a credential.
"""

import base64
import os
import time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from flowglyph.errors import ExecutionError
from flowglyph.gateway.executors._http import HttpClient

_TOKEN_MARGIN_SECONDS = 60


class _Auth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def variables(self) -> list[str]:
        """Names of the environment variables this method reads."""
        return [
            str(value)
            for name, value in self.model_dump().items()
            if name.endswith("_env") and value
        ]


class NoAuth(_Auth):
    """No credentials, for local servers and public APIs."""

    type: Literal["none"] = "none"

    def headers(self, client: HttpClient) -> dict[str, str]:
        """Nothing to add."""
        del client
        return {}


class BearerAuth(_Auth):
    """A token sent as `Authorization: Bearer ...`."""

    type: Literal["bearer"]
    token_env: str

    def headers(self, client: HttpClient) -> dict[str, str]:
        """The authorization header."""
        del client
        return {"Authorization": f"Bearer {_secret(self.token_env)}"}


class BasicAuth(_Auth):
    """A user and password sent with HTTP basic authentication."""

    type: Literal["basic"]
    user_env: str
    password_env: str

    def headers(self, client: HttpClient) -> dict[str, str]:
        """The authorization header."""
        del client
        pair = f"{_secret(self.user_env)}:{_secret(self.password_env)}".encode()
        return {"Authorization": f"Basic {base64.b64encode(pair).decode()}"}


class HeaderAuth(_Auth):
    """An API key sent in a header of the API's choosing."""

    type: Literal["header"]
    header: str
    value_env: str

    def headers(self, client: HttpClient) -> dict[str, str]:
        """The key header."""
        del client
        return {self.header: _secret(self.value_env)}


class ClientCredentialsAuth(_Auth):
    """OAuth 2.0 client credentials, as UiPath Automation Cloud and SAP BTP use them.

    The token is requested once and reused until shortly before it expires.
    """

    type: Literal["client_credentials"]
    token_url: str
    client_id_env: str
    client_secret_env: str
    scope: str | None = None
    _token: str | None = PrivateAttr(default=None)
    _expires_at: float = PrivateAttr(default=0.0)

    def headers(self, client: HttpClient) -> dict[str, str]:
        """The authorization header, fetching a token when needed.

        Raises:
            ExecutionError: If the identity server refuses the credentials.
        """
        if self._token is None or time.monotonic() >= self._expires_at:
            self._token, lifetime = self._fetch(client)
            self._expires_at = time.monotonic() + max(lifetime - _TOKEN_MARGIN_SECONDS, 0)
        return {"Authorization": f"Bearer {self._token}"}

    def _fetch(self, client: HttpClient) -> tuple[str, float]:
        form = {
            "grant_type": "client_credentials",
            "client_id": _secret(self.client_id_env),
            "client_secret": _secret(self.client_secret_env),
        }
        if self.scope:
            form["scope"] = self.scope
        response = client.request("POST", self.token_url, form=form)
        answer = response.json()
        if not response.ok or not isinstance(answer, dict) or "access_token" not in answer:
            raise ExecutionError(
                f"{self.token_url} refused the client credentials ({response.status}): "
                f"{response.snippet()}"
            )
        lifetime = float(answer.get("expires_in", 3600))  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
        return str(answer["access_token"]), lifetime  # pyright: ignore[reportUnknownArgumentType]


type Auth = Annotated[
    NoAuth | BearerAuth | BasicAuth | HeaderAuth | ClientCredentialsAuth,
    Field(discriminator="type"),
]


def _secret(variable: str) -> str:
    value = os.environ.get(variable)
    if not value:
        raise ExecutionError(f"the environment variable {variable} is not set")
    return value
