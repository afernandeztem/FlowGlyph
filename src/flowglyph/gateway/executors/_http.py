"""A small HTTP client for executors: JSON in and out, cookies kept, redirects refused."""

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from email.message import Message
from http import HTTPStatus
from http.cookiejar import CookieJar
from typing import Any

from flowglyph.errors import ExecutionError

MAX_RESPONSE_BYTES = 16 * 1024 * 1024
_SNIPPET = 300


@dataclass(frozen=True)
class Response:
    """What a server answered."""

    status: int
    headers: Message
    body: bytes = b""
    url: str = ""

    @property
    def ok(self) -> bool:
        """Whether the status reports success."""
        return self.status < HTTPStatus.BAD_REQUEST

    @property
    def redirected(self) -> bool:
        """Whether the status is a redirect."""
        return HTTPStatus.MULTIPLE_CHOICES <= self.status < HTTPStatus.BAD_REQUEST

    def header(self, name: str) -> str | None:
        """A response header, matched without regard to case."""
        return self.headers.get(name)

    def json(self) -> Any:
        """The body parsed as JSON, or as text when it is not JSON, or None when empty."""
        if not self.body:
            return None
        text = self.body.decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def snippet(self) -> str:
        """The start of the body, for error messages."""
        return self.body.decode("utf-8", errors="replace").strip()[:_SNIPPET]


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Redirects would carry credentials to wherever the server points, so none are followed."""

    def redirect_request(self, *_: Any, **__: Any) -> None:
        return None


@dataclass
class HttpClient:
    """Sends requests to one system, keeping its cookies between them."""

    timeout_seconds: float = 60.0
    cookies: CookieJar = field(default_factory=CookieJar)

    def __post_init__(self) -> None:
        self._opener = urllib.request.build_opener(
            _RefuseRedirects(), urllib.request.HTTPCookieProcessor(self.cookies)
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        query: Sequence[tuple[str, str]] = (),
        json_body: Any = None,
        form: Mapping[str, str] | None = None,
    ) -> Response:
        """Send one request and return the answer, whatever its status.

        Raises:
            ExecutionError: If the server cannot be reached or redirects elsewhere.
        """
        scheme = urllib.parse.urlsplit(url).scheme
        if scheme not in {"http", "https"}:
            raise ExecutionError(f"only http and https URLs can be called, not {url!r}")
        if query:
            separator = "&" if "?" in url else "?"
            url = url + separator + urllib.parse.urlencode(query, quote_via=urllib.parse.quote)
        sent = {"Accept": "application/json", **(headers or {})}
        data: bytes | None = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            sent["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_body is not None:
            data = json.dumps(json_body).encode()
            sent["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=sent, method=method)  # noqa: S310
        try:
            # The scheme was checked above, so urllib cannot be pointed at local files.
            with self._opener.open(request, timeout=self.timeout_seconds) as answer:
                return Response(answer.status, answer.headers, _read(answer), url)
        except urllib.error.HTTPError as error:
            response = Response(error.code, error.headers, _read(error), url)
            if response.redirected:
                target = response.header("Location") or "another address"
                raise ExecutionError(
                    f"{method} {url} redirected to {target}; use the final address in the "
                    "connection, since credentials are never sent on through a redirect"
                ) from error
            return response
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise ExecutionError(f"could not reach {url}: {reason}") from error
        except (ValueError, http.client.HTTPException) as error:
            # A header value or URL that the protocol cannot carry, such as a line break.
            raise ExecutionError(f"{method} {url} could not be sent: {error}") from error


def _read(answer: Any) -> bytes:
    body: bytes = answer.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ExecutionError(f"the response is larger than {MAX_RESPONSE_BYTES} bytes")
    return body
