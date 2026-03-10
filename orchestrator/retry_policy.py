from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryDecision:
    should_retry: bool
    reason: str
    delay_seconds: int = 0


class RetryPolicy:
    def __init__(self, max_attempts: int = 2) -> None:
        self.max_attempts = max_attempts

    def classify_error(self, error_message: str) -> str:
        msg = (error_message or "").lower()

        if any(x in msg for x in ["rate limit", "quota", "429"]):
            return "rate_limit"
        if any(x in msg for x in ["timeout", "timed out"]):
            return "timeout"
        if any(x in msg for x in ["temporary", "connection reset", "service unavailable", "503"]):
            return "transient"
        if any(x in msg for x in ["unauthorized", "401", "403", "invalid api key"]):
            return "auth"
        if any(x in msg for x in ["not found", "404", "missing file"]):
            return "not_found"
        if any(x in msg for x in ["blocked", "forbidden", "dangerous command", "outside project root"]):
            return "policy"
        return "unknown"

    def decide(self, error_message: str, attempts_so_far: int) -> RetryDecision:
        if attempts_so_far >= self.max_attempts:
            return RetryDecision(False, "Max retry attempts exceeded.")

        category = self.classify_error(error_message)

        if category == "rate_limit":
            return RetryDecision(True, "Retry after rate limit.", delay_seconds=5)

        if category in {"timeout", "transient", "unknown"}:
            return RetryDecision(True, f"Retry for {category} error.", delay_seconds=1)

        if category in {"auth", "policy", "not_found"}:
            return RetryDecision(False, f"Do not retry {category} error.")

        return RetryDecision(False, "Unhandled retry case.")
