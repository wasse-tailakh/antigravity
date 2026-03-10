from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from config.logger import get_logger

logger = get_logger("RateLimitPolicy")


@dataclass
class RateLimitStatus:
    is_limited: bool
    retry_after_seconds: float = 0.0
    reason: str = ""


class RateLimitPolicy:
    """
    Policy to handle API Rate Limits (429 RESOURCE_EXHAUSTED).
    Specifically tailored for Gemini's free tier limits and bursts.
    """

    def __init__(self, default_retry_after: float = 10.0, max_wait_time: float = 60.0):
        self.default_retry_after = default_retry_after
        self.max_wait_time = max_wait_time

    def check_error(self, error: Exception | str) -> RateLimitStatus:
        """
        Analyzes an error to determine if it's a rate limit issue and extracts retry info if possible.
        """
        err_str = str(error).lower()

        # Check for 429 or resource exhausted keywords
        if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate limit" in err_str:
            retry_after = self.default_retry_after
            
            # Try to extract 'retry in Xs'
            import re
            match = re.search(r'retry in (\d+(?:\.\d+)?)s', err_str)
            if match:
                try:
                    retry_after = float(match.group(1))
                except ValueError:
                    pass
            
            # Cap the wait time
            retry_after = min(retry_after, self.max_wait_time)
            
            return RateLimitStatus(
                is_limited=True,
                retry_after_seconds=retry_after,
                reason="Rate limit exceeded (429/Quota)."
            )
            
        return RateLimitStatus(is_limited=False)

    def wait_if_limited(self, error: Exception | str) -> bool:
        """
        Evaluates the error. If it's a rate limit, waits the required amount of time and returns True.
        Othewise returns False.
        """
        status = self.check_error(error)
        if status.is_limited:
            logger.warning(f"{status.reason} Waiting for {status.retry_after_seconds:.2f} seconds before retrying...")
            time.sleep(status.retry_after_seconds)
            return True
        return False
