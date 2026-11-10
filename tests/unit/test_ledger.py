import json
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from flowglyph.gateway import ledger as ledger_module
from flowglyph.gateway.ledger import Ledger, Ticket

TICKET = Ticket(
    key="k",
    capability="c",
    version="1.0.0",
    arguments_hash="h",
    ttl_seconds=60,
    arguments={"invoice": "INV-1"},
)
OLD_SCHEMA = """
CREATE TABLE runs (
    key TEXT PRIMARY KEY, capability TEXT NOT NULL, version TEXT NOT NULL,
    arguments_hash TEXT NOT NULL, status TEXT NOT NULL, result TEXT,
    created REAL NOT NULL, updated REAL NOT NULL, expires_at REAL NOT NULL
)
"""


@pytest.fixture
def ledger(tmp_path: Path) -> Ledger:
    return Ledger(tmp_path / "ledger.sqlite")


def test_a_key_is_claimed_once(ledger: Ledger):
    assert ledger.claim(TICKET).claimed
    second = ledger.claim(TICKET)
    assert not second.claimed
    assert second.existing is not None
    assert second.existing.status == "running"


def test_finished_runs_keep_their_result(ledger: Ledger):
    ledger.claim(TICKET)
    ledger.finish("k", "done", {"invoice": 42})
    run = ledger.get("k")
    assert run is not None
    assert (run.status, run.result) == ("done", {"invoice": 42})


def test_failed_runs_can_be_retried(ledger: Ledger):
    ledger.claim(TICKET)
    ledger.finish("k", "failed", {"error": "timeout"})
    assert ledger.claim(TICKET).claimed


def test_expired_keys_are_released(ledger: Ledger, monkeypatch: pytest.MonkeyPatch):
    ledger.claim(TICKET)
    ledger.finish("k", "done", {})
    real_time = ledger_module.time.time
    monkeypatch.setattr(ledger_module.time, "time", lambda: real_time() + 3600)
    assert ledger.claim(TICKET).claimed


def test_concurrent_claims_have_a_single_winner(ledger: Ledger):
    barrier = threading.Barrier(16)
    winners: list[bool] = []

    def contend() -> None:
        barrier.wait()
        winners.append(ledger.claim(TICKET).claimed)

    threads = [threading.Thread(target=contend) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert winners.count(True) == 1


def test_approval_is_consumed_only_by_a_run(ledger: Ledger):
    assert ledger.claim(TICKET, status="awaiting_approval").claimed
    assert [run.key for run in ledger.pending_approvals()] == ["k"]
    approved = ledger.approve("k")
    assert approved is not None
    assert (approved.status, approved.arguments) == ("approved", {"invoice": "INV-1"})
    assert ledger.approve("k") is None, "approving twice does nothing"
    assert not ledger.claim(TICKET, status="awaiting_approval").claimed, "approval is kept"
    assert ledger.claim(TICKET, status="running").claimed
    assert ledger.pending_approvals() == []


def test_ledgers_written_before_arguments_were_kept_still_open(tmp_path: Path):
    path = tmp_path / "ledger.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(OLD_SCHEMA)
        connection.execute(
            "INSERT INTO runs VALUES ('old', 'c', '1.0.0', 'h', 'awaiting_approval', "
            "NULL, 1, 1, ?)",
            (2e12,),
        )
    ledger = Ledger(path)
    old = ledger.get("old")
    assert old is not None
    assert (old.status, old.arguments) == ("awaiting_approval", None)
    assert ledger.claim(TICKET).claimed
    new = ledger.get("k")
    assert new is not None
    assert new.arguments == {"invoice": "INV-1"}


def test_a_real_run_takes_the_key_from_a_dry_run(tmp_path: Path):
    ledger = Ledger(tmp_path / "ledger.sqlite")
    rehearsal = Ticket("k", "cap", "1.0.0", "hash", 60, dry_run=True)
    real = Ticket("k", "cap", "1.0.0", "hash", 60)
    assert ledger.claim(rehearsal).claimed
    ledger.finish("k", "done", {"dry_run": True})
    assert not ledger.claim(rehearsal).claimed
    assert ledger.claim(real).claimed
    ledger.finish("k", "done", {"ok": True})
    assert not ledger.claim(real).claimed
    replayed = ledger.claim(rehearsal)
    assert replayed.existing is not None
    assert replayed.existing.result == {"ok": True}


def test_dry_runs_recorded_before_the_ledger_marked_them_are_recognised(tmp_path: Path):
    path = tmp_path / "ledger.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE runs (key TEXT PRIMARY KEY, capability TEXT NOT NULL, "
            "version TEXT NOT NULL, arguments_hash TEXT NOT NULL, status TEXT NOT NULL, "
            "result TEXT, created REAL NOT NULL, updated REAL NOT NULL, "
            "expires_at REAL NOT NULL, arguments TEXT)"
        )
        connection.execute(
            "INSERT INTO runs VALUES ('k', 'cap', '1.0.0', 'hash', 'done', ?, 0, 0, ?, NULL)",
            (json.dumps({"dry_run": True, "would_run": "x"}), time.time() + 60),
        )
    connection.close()
    assert Ledger(path).claim(Ticket("k", "cap", "1.0.0", "hash", 60)).claimed
