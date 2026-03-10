from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

class FailureCategory(Enum):
    RETRYABLE = auto()
    NON_RETRYABLE = auto()
    POLICY_VIOLATION = auto()
    RATE_LIMIT = auto()
    AUTH_ERROR = auto()
    UNKNOWN = auto()

@dataclass
class RetryDecision:
    should_retry: bool
    reason: str
    delay_seconds: int = 0
    category: FailureCategory = FailureCategory.UNKNOWN
    should_escalate: bool = False

class RetryPolicy:
    def __init__(self, max_attempts: int = 3) -> None:
        self.max_attempts = max_attempts

    def classify_error(self, error_message: str) -> FailureCategory:
        msg = (error_message or "").lower()

        if any(x in msg for x in ["rate limit", "quota", "429", "resource_exhausted"]):
            return FailureCategory.RATE_LIMIT
            
        if any(x in msg for x in ["unauthorized", "invalid api key", "401", "403"]):
            return FailureCategory.AUTH_ERROR
            
        if any(x in msg for x in ["security violation", "blocked", "forbidden", "dangerous command", "costguard threshold"]):
            return FailureCategory.POLICY_VIOLATION
            
        if any(x in msg for x in ["timeout", "timed out", "temporary", "connection reset", "service unavailable", "503"]):
            return FailureCategory.RETRYABLE
            
        if any(x in msg for x in ["syntax error", "type error", "value error", "not found"]):
            return FailureCategory.RETRYABLE # We might want to try again with feedback
            
        return FailureCategory.UNKNOWN

    def decide(self, error_message: str, attempts_so_far: int) -> RetryDecision:
        category = self.classify_error(error_message)

        if category == FailureCategory.RATE_LIMIT:
            # We let backoff handle actual rate limits usually, but if it bubbles up here:
            return RetryDecision(True, "Rate limit hit.", delay_seconds=5, category=category)

        if category == FailureCategory.AUTH_ERROR:
            return RetryDecision(False, "Authentication error. Cannot proceed without fixing keys.", category=category)

        if category == FailureCategory.POLICY_VIOLATION:
            return RetryDecision(False, "Policy or security violation. Halting.", category=category)

        if attempts_so_far >= self.max_attempts:
            return RetryDecision(False, "Max retry attempts exceeded.", category=category, should_escalate=True)

        if category in {FailureCategory.RETRYABLE, FailureCategory.UNKNOWN}:
            # Escalation heuristic: If we failed twice on a reasoning task, escalate to Claude for the final attempt
            escalate = (attempts_so_far == self.max_attempts - 1)
            return RetryDecision(True, f"Retrying task (attempt {attempts_so_far + 1}/{self.max_attempts}).", delay_seconds=1, category=category, should_escalate=escalate)

        return RetryDecision(False, "Unhandled error category.", category=category)
