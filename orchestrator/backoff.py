from __future__ import annotations

import random
import time
from typing import Callable, TypeVar, Any

from config.logger import get_logger

logger = get_logger("Backoff")

T = TypeVar('T')

class BackoffLogic:
    """
    Implements exponential backoff with jitter for retrying operations.
    """

    @staticmethod
    def execute_with_backoff(
        operation: Callable[[], T],
        max_attempts: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
        jitter_factor: float = 0.5,
        rate_limit_policy: Any = None
    ) -> T:
        """
        Executes a callable with exponential backoff on exceptions.
        If a rate_limit_policy is provided, it integrates with it to coordinate wait times for 429s.
        """
        attempt = 1
        
        while attempt <= max_attempts:
            try:
                return operation()
            except Exception as e:
                # If it's the last attempt, just raise
                if attempt == max_attempts:
                    logger.error(f"Operation failed after {max_attempts} attempts. Last error: {e}")
                    raise
                    
                # Ask rate limit policy if this is a known rate limit (it might do a specific sleep)
                handled_by_rl = False
                if rate_limit_policy:
                     handled_by_rl = rate_limit_policy.wait_if_limited(e)
                     
                # If not specifically handled (or even if it was, but we still need to backoff for the next attempt)
                # calculate exponential backoff if the RL didn't intercept it or if RL just returns true after waiting
                if not handled_by_rl:
                    # Exponential delay
                    delay = base_delay * (2 ** (attempt - 1))
                    
                    # Add jitter
                    jitter = delay * jitter_factor
                    delay = delay + random.uniform(-jitter, jitter)
                    
                    delay = min(delay, max_delay)
                    
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                
                attempt += 1
                
        raise Exception("Max attempts reached") # Should not be hit due to raise in loop
