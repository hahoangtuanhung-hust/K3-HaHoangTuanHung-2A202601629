"""
Assignment 11 — Audit Log (TODO 8).

Records every interaction for forensics and compliance review.
This layer never blocks by itself — other layers catch attacks;
this layer makes them auditable and replayable.

Key design:
- request_id is a correlation ID that ties input → output together.
- latency_seconds measures end-to-end processing time per request.
- layer indicates which guardrail layer made the blocking decision.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


class AuditLogPlugin:
    """
    TODO 8 — Framework-agnostic audit logger.

    Wire into ADK callbacks or your pipeline via record_input / record_output.
    Each request is tracked by a correlation request_id so you can join
    input and output log entries for forensic replay.
    """

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        # In-flight requests: request_id -> {start_ts, input_text}
        self._open: dict[str, dict] = {}

    def record_input(
        self,
        *,
        user_id: str,
        text: str,
        request_id: str | None = None,
    ) -> None:
        """
        TODO 8 — Record an incoming user message.

        Stores a start timestamp keyed by request_id so latency can be
        computed when record_output is called.

        Args:
            user_id:    Identifier for the user making the request.
            text:       The raw user input text.
            request_id: Correlation ID. If None, falls back to user_id.
        """
        key = request_id or user_id
        self._open[key] = {
            "start_ts": datetime.now(timezone.utc).timestamp(),
            "input_text": text,
        }

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """
        TODO 8 — Record the agent response and append a complete audit entry.

        Args:
            user_id:    Identifier for the user making the request.
            text:       The agent's response text.
            blocked:    True if the request was blocked by any guardrail.
            layer:      Name of the layer that made the blocking decision,
                        e.g. "rate_limiter", "input_guardrail", "output_guardrail".
            request_id: Correlation ID matching the one used in record_input.
        """
        key = request_id or user_id
        open_entry = self._open.pop(key, {})
        start_ts = open_entry.get("start_ts", datetime.now(timezone.utc).timestamp())
        input_text = open_entry.get("input_text", "")
        latency = datetime.now(timezone.utc).timestamp() - start_ts

        log_entry = {
            "timestamp": _utc_now_iso(),
            "request_id": request_id or user_id,
            "user_id": user_id,
            "input": input_text,
            "output": text,
            "blocked": blocked,
            "blocking_layer": layer,         # which guardrail blocked (or None)
            "latency_seconds": round(latency, 4),
        }
        self.logs.append(log_entry)

    def export_json(self, filepath: str = "outputs/audit_log.json") -> None:
        """
        Write the full audit log to disk as a JSON array.

        Each element is one request/response pair with correlation ID,
        timestamps, blocking decision, and latency.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)

    def snapshot(self) -> list[dict]:
        """Return a copy of the current audit log entries."""
        return list(self.logs)


def _utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
