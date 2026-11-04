import threading
from pathlib import Path

import pytest

from flowglyph.gateway import ledger as ledger_module
from flowglyph.gateway.ledger import Ledger, Ticket

TICKET = Ticket(key="k", capability="c", version="1.0.0", arguments_hash="h", ttl_seconds=60)


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
    assert ledger.approve("k")
    assert not ledger.approve("k"), "approving twice does nothing"
    assert not ledger.claim(TICKET, status="awaiting_approval").claimed, "approval is kept"
    assert ledger.claim(TICKET, status="running").claimed
    assert ledger.pending_approvals() == []
