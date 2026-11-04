import json
import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

type RunStatus = Literal["running", "done", "failed", "awaiting_approval", "approved"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    key TEXT PRIMARY KEY,
    capability TEXT NOT NULL,
    version TEXT NOT NULL,
    arguments_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    result TEXT,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    expires_at REAL NOT NULL
)
"""


@dataclass(frozen=True)
class Run:
    """One row of the ledger."""

    key: str
    capability: str
    version: str
    arguments_hash: str
    status: RunStatus
    result: Any
    created: float
    updated: float
    expires_at: float


@dataclass(frozen=True)
class Ticket:
    """A request to run one capability under one idempotency key."""

    key: str
    capability: str
    version: str
    arguments_hash: str
    ttl_seconds: int


@dataclass(frozen=True)
class Claim:
    """Outcome of trying to start a run under an idempotency key.

    `claimed` is true when the caller now owns the key and must execute and then call
    `Ledger.finish`. Otherwise `existing` describes the run that already holds it.
    """

    claimed: bool
    existing: Run | None = None


class Ledger:
    """Durable record of runs, keyed by idempotency key.

    Claiming a key is a single `INSERT ... ON CONFLICT DO NOTHING`, so two concurrent calls
    with the same key can never both execute, even from different processes.
    """

    def __init__(self, path: str | Path) -> None:
        """Open, and create if needed, the ledger at `path`."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(_SCHEMA)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        try:
            yield connection
        finally:
            connection.close()

    def claim(self, ticket: Ticket, status: RunStatus = "running") -> Claim:
        """Try to take ownership of the ticket's key, resuming runs that failed or expired."""
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM runs WHERE key = ? AND expires_at < ?", (ticket.key, now)
            )
            inserted = connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?) "
                "ON CONFLICT(key) DO NOTHING",
                (
                    ticket.key,
                    ticket.capability,
                    ticket.version,
                    ticket.arguments_hash,
                    status,
                    now,
                    now,
                    now + ticket.ttl_seconds,
                ),
            ).rowcount
            if inserted:
                return Claim(claimed=True)
            # An approval may only be consumed by the run it approved, never reset to waiting.
            resumable = ("failed", "approved") if status == "running" else ("failed", "failed")
            retried = connection.execute(
                "UPDATE runs SET status = ?, updated = ? "
                "WHERE key = ? AND arguments_hash = ? AND status IN (?, ?)",
                (status, now, ticket.key, ticket.arguments_hash, *resumable),
            ).rowcount
            if retried:
                return Claim(claimed=True)
        return Claim(claimed=False, existing=self.get(ticket.key))

    def finish(self, key: str, status: Literal["done", "failed"], result: Any) -> None:
        """Record the outcome of a claimed run."""
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status = ?, result = ?, updated = ? WHERE key = ?",
                (status, json.dumps(result, default=str), time.time(), key),
            )

    def approve(self, key: str) -> bool:
        """Approve a run that is waiting for approval. Returns whether one was waiting."""
        with self._connect() as connection:
            return bool(
                connection.execute(
                    "UPDATE runs SET status = 'approved', updated = ? "
                    "WHERE key = ? AND status = 'awaiting_approval'",
                    (time.time(), key),
                ).rowcount
            )

    def get(self, key: str) -> Run | None:
        """The run stored under `key`, if any."""
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE key = ?", (key,)).fetchone()
        return _run(row) if row else None

    def pending_approvals(self) -> list[Run]:
        """Runs waiting for a person to approve them, oldest first."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs WHERE status = 'awaiting_approval' ORDER BY created"
            ).fetchall()
        return [_run(row) for row in rows]


def _run(row: tuple[Any, ...]) -> Run:
    key, capability, version, arguments_hash, status, result, created, updated, expires = row
    return Run(
        key=key,
        capability=capability,
        version=version,
        arguments_hash=arguments_hash,
        status=status,
        result=json.loads(result) if result else None,
        created=created,
        updated=updated,
        expires_at=expires,
    )
