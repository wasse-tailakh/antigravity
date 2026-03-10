"""
Adaptive Backoff Algorithm with Learning Capabilities

This algorithm learns from historical failures and adapts retry strategies
dynamically based on provider-specific patterns and time-of-day trends.
"""

from __future__ import annotations

import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, TypeVar, Any
import json

from config.logger import get_logger

logger = get_logger("AdaptiveBackoff")

T = TypeVar('T')


class BackoffStrategy(Enum):
    """Different backoff strategies for different failure types"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    DECORRELATED_JITTER = "decorrelated_jitter"


@dataclass
class ProviderMetrics:
    """Track historical metrics per provider"""
    provider_name: str
    total_calls: int = 0
    failed_calls: int = 0
    rate_limit_hits: int = 0
    avg_response_time: float = 0.0
    last_rate_limit_at: float = 0.0
    success_rate_by_hour: dict[int, float] = field(default_factory=dict)
    optimal_delay: float = 2.0  # Learned optimal base delay

    def update_success_rate(self, hour: int, success: bool):
        """Track success rates by hour of day"""
        if hour not in self.success_rate_by_hour:
            self.success_rate_by_hour[hour] = 1.0 if success else 0.0
        else:
            # Exponential moving average
            alpha = 0.3
            current_rate = self.success_rate_by_hour[hour]
            new_value = 1.0 if success else 0.0
            self.success_rate_by_hour[hour] = alpha * new_value + (1 - alpha) * current_rate

    def get_failure_rate(self) -> float:
        """Calculate current failure rate"""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls

    def adjust_optimal_delay(self, success: bool):
        """Dynamically adjust optimal delay based on outcomes"""
        if success:
            # Successful retry - can be more aggressive
            self.optimal_delay = max(0.5, self.optimal_delay * 0.9)
        else:
            # Failed retry - back off more
            self.optimal_delay = min(30.0, self.optimal_delay * 1.5)


class AdaptiveBackoff:
    """
    Intelligent backoff that learns from past failures and adapts strategy.

    Features:
    - Provider-specific learning
    - Time-of-day awareness
    - Multiple backoff strategies
    - Automatic strategy switching
    - Predictive rate limit avoidance
    """

    def __init__(
        self,
        cache_dir: str | Path = ".cache/backoff_metrics",
        enable_learning: bool = True,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enable_learning = enable_learning

        # Per-provider metrics
        self.provider_metrics: dict[str, ProviderMetrics] = {}

        # Load historical data
        self._load_metrics()

    def _load_metrics(self):
        """Load historical metrics from disk"""
        metrics_file = self.cache_dir / "provider_metrics.json"
        if metrics_file.exists():
            try:
                with metrics_file.open("r") as f:
                    data = json.load(f)
                    for provider_name, metrics_data in data.items():
                        self.provider_metrics[provider_name] = ProviderMetrics(
                            provider_name=provider_name,
                            **metrics_data
                        )
                logger.info(f"Loaded metrics for {len(self.provider_metrics)} providers")
            except Exception as e:
                logger.warning(f"Failed to load backoff metrics: {e}")

    def _save_metrics(self):
        """Persist metrics to disk for future learning"""
        if not self.enable_learning:
            return

        metrics_file = self.cache_dir / "provider_metrics.json"
        try:
            data = {
                name: {
                    "total_calls": m.total_calls,
                    "failed_calls": m.failed_calls,
                    "rate_limit_hits": m.rate_limit_hits,
                    "avg_response_time": m.avg_response_time,
                    "last_rate_limit_at": m.last_rate_limit_at,
                    "success_rate_by_hour": m.success_rate_by_hour,
                    "optimal_delay": m.optimal_delay,
                }
                for name, m in self.provider_metrics.items()
            }
            with metrics_file.open("w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save backoff metrics: {e}")

    def _get_provider_metrics(self, provider: str) -> ProviderMetrics:
        """Get or create metrics for a provider"""
        if provider not in self.provider_metrics:
            self.provider_metrics[provider] = ProviderMetrics(provider_name=provider)
        return self.provider_metrics[provider]

    def _select_strategy(
        self,
        provider: str,
        attempt: int,
        error_type: str | None = None,
    ) -> BackoffStrategy:
        """
        Intelligently select backoff strategy based on context.

        - Rate limits: Use decorrelated jitter to avoid thundering herd
        - High failure rate: Use exponential backoff
        - Transient errors: Use fibonacci for gradual increase
        - Otherwise: Linear backoff
        """
        metrics = self._get_provider_metrics(provider)

        if error_type and "rate" in error_type.lower():
            return BackoffStrategy.DECORRELATED_JITTER

        failure_rate = metrics.get_failure_rate()

        if failure_rate > 0.5:
            # High failure rate - be more aggressive
            return BackoffStrategy.EXPONENTIAL
        elif failure_rate > 0.2:
            # Moderate failures - gradual increase
            return BackoffStrategy.FIBONACCI
        else:
            # Low failure rate - simple linear
            return BackoffStrategy.LINEAR

    def _calculate_delay(
        self,
        strategy: BackoffStrategy,
        attempt: int,
        base_delay: float,
        max_delay: float,
        last_delay: float = 0.0,
    ) -> float:
        """Calculate delay based on strategy"""

        if strategy == BackoffStrategy.EXPONENTIAL:
            delay = base_delay * (2 ** (attempt - 1))

        elif strategy == BackoffStrategy.LINEAR:
            delay = base_delay * attempt

        elif strategy == BackoffStrategy.FIBONACCI:
            # Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13...
            def fib(n):
                if n <= 2:
                    return 1
                a, b = 1, 1
                for _ in range(n - 2):
                    a, b = b, a + b
                return b
            delay = base_delay * fib(attempt)

        elif strategy == BackoffStrategy.DECORRELATED_JITTER:
            # AWS recommended: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
            # delay = random_between(base_delay, last_delay * 3)
            delay = random.uniform(base_delay, max(base_delay, last_delay * 3))
        else:
            delay = base_delay * attempt

        # Apply jitter to all strategies (except decorrelated which has its own)
        if strategy != BackoffStrategy.DECORRELATED_JITTER:
            jitter = delay * 0.3  # 30% jitter
            delay = delay + random.uniform(-jitter, jitter)

        return min(delay, max_delay)

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Detect if error is rate limit related"""
        error_str = str(error).lower()
        return any(
            indicator in error_str
            for indicator in [
                "rate limit",
                "quota",
                "429",
                "resource_exhausted",
                "too many requests",
            ]
        )

    def _should_predict_rate_limit(self, provider: str) -> tuple[bool, float]:
        """
        Predict if we're about to hit rate limit based on historical patterns.

        Returns:
            (should_wait, recommended_delay)
        """
        metrics = self._get_provider_metrics(provider)

        # Check if we recently hit rate limit
        time_since_last_rl = time.time() - metrics.last_rate_limit_at

        if time_since_last_rl < 60:  # Within last minute
            # Very likely to hit again, proactive wait
            return True, 5.0

        # Check time-of-day patterns
        current_hour = datetime.now().hour
        if current_hour in metrics.success_rate_by_hour:
            success_rate = metrics.success_rate_by_hour[current_hour]
            if success_rate < 0.5:  # Less than 50% success rate this hour
                # This hour tends to have issues
                return True, 2.0

        return False, 0.0

    def execute_with_adaptive_backoff(
        self,
        operation: Callable[[], T],
        provider: str = "unknown",
        max_attempts: int = 5,
        base_delay: float | None = None,
        max_delay: float = 60.0,
        error_callback: Callable[[Exception, int], None] | None = None,
    ) -> T:
        """
        Execute operation with intelligent adaptive backoff.

        Args:
            operation: The function to execute
            provider: Provider name (gemini, claude, openai) for tracking
            max_attempts: Maximum retry attempts
            base_delay: Base delay (auto-learned if None)
            max_delay: Maximum delay cap
            error_callback: Optional callback on each error

        Returns:
            Result from successful operation

        Raises:
            Exception from last failed attempt
        """
        metrics = self._get_provider_metrics(provider)

        # Use learned optimal delay if not specified
        if base_delay is None:
            base_delay = metrics.optimal_delay

        # Predictive rate limit avoidance
        should_wait, proactive_delay = self._should_predict_rate_limit(provider)
        if should_wait:
            logger.info(
                f"Proactively waiting {proactive_delay}s for {provider} "
                f"based on historical patterns"
            )
            time.sleep(proactive_delay)

        attempt = 1
        last_delay = 0.0
        last_error = None
        start_time = time.time()

        while attempt <= max_attempts:
            try:
                # Execute operation
                result = operation()

                # Success! Update metrics
                metrics.total_calls += 1
                response_time = time.time() - start_time

                # Update average response time (exponential moving average)
                if metrics.avg_response_time == 0:
                    metrics.avg_response_time = response_time
                else:
                    metrics.avg_response_time = (
                        0.7 * metrics.avg_response_time + 0.3 * response_time
                    )

                # Update hourly success rate
                current_hour = datetime.now().hour
                metrics.update_success_rate(current_hour, success=True)

                # Learn from success
                if attempt > 1:  # Was a retry
                    metrics.adjust_optimal_delay(success=True)
                    logger.info(
                        f"Retry succeeded for {provider}. "
                        f"New optimal delay: {metrics.optimal_delay:.2f}s"
                    )

                # Persist learning
                self._save_metrics()

                return result

            except Exception as e:
                last_error = e
                metrics.total_calls += 1
                metrics.failed_calls += 1

                # Update hourly failure rate
                current_hour = datetime.now().hour
                metrics.update_success_rate(current_hour, success=False)

                # Check if rate limit
                is_rate_limit = self._is_rate_limit_error(e)
                if is_rate_limit:
                    metrics.rate_limit_hits += 1
                    metrics.last_rate_limit_at = time.time()

                # Callback
                if error_callback:
                    error_callback(e, attempt)

                # Last attempt - fail
                if attempt == max_attempts:
                    metrics.adjust_optimal_delay(success=False)
                    self._save_metrics()
                    logger.error(
                        f"Operation failed after {max_attempts} attempts for {provider}. "
                        f"Last error: {e}"
                    )
                    raise

                # Select strategy
                error_type = "rate_limit" if is_rate_limit else "general"
                strategy = self._select_strategy(provider, attempt, error_type)

                # Calculate delay
                delay = self._calculate_delay(
                    strategy=strategy,
                    attempt=attempt,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    last_delay=last_delay,
                )
                last_delay = delay

                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed for {provider} "
                    f"(strategy={strategy.value}): {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)
                attempt += 1

        # Should never reach here due to raise in loop
        raise Exception(f"Max attempts ({max_attempts}) reached") from last_error

    def get_provider_stats(self, provider: str) -> dict[str, Any]:
        """Get statistics for a provider"""
        if provider not in self.provider_metrics:
            return {}

        metrics = self.provider_metrics[provider]
        return {
            "provider": provider,
            "total_calls": metrics.total_calls,
            "failed_calls": metrics.failed_calls,
            "success_rate": 1.0 - metrics.get_failure_rate(),
            "rate_limit_hits": metrics.rate_limit_hits,
            "avg_response_time": metrics.avg_response_time,
            "optimal_delay": metrics.optimal_delay,
            "hourly_patterns": metrics.success_rate_by_hour,
        }

    def reset_provider_stats(self, provider: str):
        """Reset statistics for a provider"""
        if provider in self.provider_metrics:
            del self.provider_metrics[provider]
            self._save_metrics()
