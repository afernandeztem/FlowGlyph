"""Send ReFrameWork workflows through the gateway the way an agent would, and print the outcome."""

import tempfile
from pathlib import Path

from flowglyph.gateway import Gateway, Policy

HERE = Path(__file__).parent
GET = "uipath/ReFrameWork/Framework/GetTransactionData"
SET = "uipath/ReFrameWork/Framework/SetTransactionStatus"

with tempfile.TemporaryDirectory() as state:
    gateway = Gateway(HERE / "catalog", policy=Policy.load(HERE / "policy.yaml"), state_dir=state)

    take = {"in_TransactionNumber": 1, "in_Config": {}, "io_TransactionData": {}}
    first = gateway.run(GET, take, idempotency_key="run-42/transaction-1")
    retry = gateway.run(GET, take, idempotency_key="run-42/transaction-1")
    print(f"take an item: {first.status}, retried: {retry.status}")

    status = {
        "in_Config": {},
        "in_SystemError": None,
        "in_BusinessRuleException": None,
        "io_RetryNumber": 0,
        "io_TransactionNumber": 1,
        "in_TransactionField1": "",
        "in_TransactionField2": "",
        "in_TransactionID": "INV-2291",
    }
    done = gateway.run(SET, status)
    again = gateway.run(SET, status)
    print(f"set its status: {done.status}, again: {again.status}, key {again.idempotency_key}")

    tests = gateway.run("uipath/ReFrameWork/Tests/RunAllTests", {})
    print(f"run the tests: {tests.status}, {tests.reason}")

    main = gateway.run("uipath/ReFrameWork/Main", {"in_OrchestratorQueueName": "AP_Invoices"})
    why, _, how = (main.reason or "").partition("; ")
    print(f"start the process: {main.status}, {why}")
    print(f"  {how}")

    shot = gateway.run("uipath/activity/TakeScreenshot", {})
    print(f"an activity type: {shot.status}, {shot.errors[0]}")
