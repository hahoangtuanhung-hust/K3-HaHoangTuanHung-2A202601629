"""
Assignment 11 — Monitoring & Alerts (TODO 8).

Tracks aggregate block rate, rate-limit hits, and judge failure rate.
Fires alerts when configured thresholds are exceeded, enabling incident
response and correlation with audit log entries.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class Alert:
    """A single monitoring alert fired when a threshold is breached."""
    metric: str
    value: float
    threshold: float
    message: str


@dataclass
class MonitoringAlert:
    """
    TODO 8 — Aggregate counters from pipeline plugins and emit alerts.

    Update counters after each request, then call check_metrics() at
    end of a batch (or periodically) to compute rates and fire alerts.
    All counters and thresholds can be overridden at construction time.
    """

    # Alert thresholds
    block_rate_threshold: float = 0.5       # alert if >50% of requests blocked
    rate_limit_hit_threshold: int = 5       # alert if >5 rate-limit hits
    judge_fail_rate_threshold: float = 0.3  # alert if >30% judge checks fail

    alerts: list[Alert] = field(default_factory=list)

    # Counters — updated by run_assignment_suite after each request
    total_requests: int = 0
    blocked_requests: int = 0
    rate_limit_hits: int = 0
    judge_checks: int = 0
    judge_fails: int = 0

    def check_metrics(self) -> list[Alert]:
        """
        TODO 8 — Compute rates and append Alert objects when thresholds exceeded.

        Evaluates three metrics:
          - block_rate:      blocked_requests / total_requests
          - rate_limit_hits: absolute count of rate-limit blocks
          - judge_fail_rate: judge_fails / judge_checks

        Returns:
            List of Alert objects for any threshold breach (also stored in self.alerts).
        """
        self.alerts = []

        # 1. Block rate alert
        block_rate = (
            self.blocked_requests / self.total_requests
            if self.total_requests
            else 0.0
        )
        if block_rate > self.block_rate_threshold:
            self.alerts.append(Alert(
                metric="block_rate",
                value=round(block_rate, 4),
                threshold=self.block_rate_threshold,
                message=f"Block rate {block_rate:.1%} exceeded threshold {self.block_rate_threshold:.1%}",
            ))

        # 2. Rate-limit hit alert
        if self.rate_limit_hits > self.rate_limit_hit_threshold:
            self.alerts.append(Alert(
                metric="rate_limit_hits",
                value=self.rate_limit_hits,
                threshold=self.rate_limit_hit_threshold,
                message="Rate limit hits exceeded threshold",
            ))

        # 3. Judge failure rate alert
        judge_fail_rate = (
            self.judge_fails / self.judge_checks
            if self.judge_checks
            else 0.0
        )
        if judge_fail_rate > self.judge_fail_rate_threshold:
            self.alerts.append(Alert(
                metric="judge_fail_rate",
                value=round(judge_fail_rate, 4),
                threshold=self.judge_fail_rate_threshold,
                message=f"Judge fail rate {judge_fail_rate:.1%} exceeded threshold {self.judge_fail_rate_threshold:.1%}",
            ))

        return self.alerts

    def export_json(self, filepath: str = "outputs/metrics.json") -> None:
        """
        TODO 8 — Write metrics + alerts snapshot to JSON.

        The output file includes all counters, computed rates, and
        any alerts that were fired by the last check_metrics() call.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.snapshot(), f, indent=2, ensure_ascii=False)

    def snapshot(self) -> dict:
        """Return a dictionary snapshot of all current metrics and alerts."""
        block_rate = (
            self.blocked_requests / self.total_requests
            if self.total_requests
            else 0.0
        )
        judge_fail_rate = (
            self.judge_fails / self.judge_checks if self.judge_checks else 0.0
        )
        return {
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "block_rate": round(block_rate, 4),
            "rate_limit_hits": self.rate_limit_hits,
            "judge_checks": self.judge_checks,
            "judge_fails": self.judge_fails,
            "judge_fail_rate": round(judge_fail_rate, 4),
            "alerts": [
                {
                    "metric": a.metric,
                    "value": a.value,
                    "threshold": a.threshold,
                    "message": a.message,
                }
                for a in self.alerts
            ],
        }
