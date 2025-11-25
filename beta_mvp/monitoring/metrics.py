from __future__ import annotations

import threading
import time
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class VerificationStats:
    total_requests: int = 0
    total_time_seconds: float = 0.0

    @property
    def avg_time_seconds(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_time_seconds / self.total_requests


class MetricsRegistry:
    """In-memory metrics registry.

    For a production system, back this with Prometheus, StatsD, or a DB.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.verification_stats = VerificationStats()
        self.language_counts: Counter[str] = Counter()
        # Reviewer feedback: true/false positives/negatives
        self.review_outcomes: Counter[str] = Counter()
        # Claim categories (simple string labels)
        self.claim_categories: Counter[str] = Counter()

    # ---- Verification time ----

    def record_verification_time(self, duration_seconds: float) -> None:
        with self._lock:
            self.verification_stats.total_requests += 1
            self.verification_stats.total_time_seconds += max(0.0, duration_seconds)

    # ---- Language distribution ----

    def record_language(self, language_code: str) -> None:
        if not language_code:
            return
        with self._lock:
            self.language_counts[language_code] += 1

    # ---- Reviewer outcomes ----

    def record_review_outcome(self, outcome_label: str) -> None:
        """Outcome labels might be 'true_positive', 'false_positive', etc."""
        if not outcome_label:
            return
        with self._lock:
            self.review_outcomes[outcome_label] += 1

    # ---- Claim categories ----

    def record_claim_category(self, category: str) -> None:
        if not category:
            return
        with self._lock:
            self.claim_categories[category] += 1

    # ---- Snapshot ----

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "verification": {
                    **asdict(self.verification_stats),
                    "avg_time_seconds": self.verification_stats.avg_time_seconds,
                },
                "languages": dict(self.language_counts),
                "review_outcomes": dict(self.review_outcomes),
                "claim_categories": dict(self.claim_categories),
            }


_registry = MetricsRegistry()


def record_verification_time(duration_seconds: float) -> None:
    _registry.record_verification_time(duration_seconds)


def record_language(language_code: str) -> None:
    _registry.record_language(language_code)


def record_review_outcome(outcome_label: str) -> None:
    _registry.record_review_outcome(outcome_label)


def record_claim_category(category: str) -> None:
    _registry.record_claim_category(category)


def get_metrics_snapshot() -> Dict[str, Any]:
    return _registry.snapshot()
