import json
import threading
import time
from pathlib import Path
from typing import Any


class AuditLog:
    """Append-only JSON Lines record of every call the gateway handles.

    Argument values are never written, only their names and a hash, because they routinely
    contain personal data or secrets. The hash is enough to correlate a call with its ledger
    entry.
    """

    def __init__(self, path: str | Path) -> None:
        """Append to the log at `path`, creating it if needed."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(self, event: str, **fields: Any) -> None:
        """Append one event."""
        entry = {"time": round(time.time(), 3), "event": event, **fields}
        line = json.dumps(entry, sort_keys=True, default=str)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
