"""
Circuit Breaker Pattern Implementation for API Resilience

Protects the system from cascading failures by "opening" the circuit
when a service is failing, giving it time to recover.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests fail fast without calling
- HALF_OPEN: Testing if service recovered, limited requests allowed
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, TypeVar, Any, Optional
from pathlib import Path
import json

from config.logger import get_logger

logger = get_logger("CircuitBreaker")

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitMetrics:
    """Metrics for a circuit"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    state_changes: int = 0

    # Rolling window for failure rate calculation
    recent_results: deque = field(default_factory=lambda: deque(maxlen=100))

    def get_failure_rate(self) -> float:
        """Calculate failure rate from recent results"""
        if not self.recent_results:
            return 0.0
        failures = sum(1 for result in self.recent_results if not result)
        return failures / len(self.recent_results)

    def get_success_rate(self) -> float:
        """Calculate success rate from recent results"""
        return 1.0 - self.get_failure_rate()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit is open and request is blocked"""
    pass


class CircuitBreaker:
    """
    Advanced Circuit Breaker with adaptive thresholds.

    Features:
    - Three-state operation (CLOSED, OPEN, HALF_OPEN)
    - Rolling window failure tracking
    - Adaptive timeout based on historical recovery times
    - Per-service circuit management
    - Automatic health monitoring
    - Graceful degradation support
    """

    def __init__(
        self,
        failure_threshold: int = 5,  # Failures before opening
        success_threshold: int = 2,  # Successes in half-open before closing
        timeout: float = 30.0,  # Seconds before trying half-open
        window_size: int = 100,  # Size of rolling window
        failure_rate_threshold: float = 0.5,  # 50% failure rate triggers open
        enable_adaptive_timeout: bool = True,
        cache_dir: str | Path = ".cache/circuit_breaker",
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.base_timeout = timeout
        self.window_size = window_size
        self.failure_rate_threshold = failure_rate_threshold
        self.enable_adaptive_timeout = enable_adaptive_timeout
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Per-service circuits
        self.circuits: dict[str, CircuitState] = {}
        self.metrics: dict[str, CircuitMetrics] = {}
        self.opened_at: dict[str, float] = {}
        self.adaptive_timeouts: dict[str, float] = {}

        # Thread safety
        self.locks: dict[str, threading.Lock] = {}

        # Load persisted state
        self._load_state()

    def _get_lock(self, service: str) -> threading.Lock:
        """Get or create lock for a service"""
        if service not in self.locks:
            self.locks[service] = threading.Lock()
        return self.locks[service]

    def _get_metrics(self, service: str) -> CircuitMetrics:
        """Get or create metrics for a service"""
        if service not in self.metrics:
            self.metrics[service] = CircuitMetrics()
        return self.metrics[service]

    def _get_state(self, service: str) -> CircuitState:
        """Get current state of circuit"""
        if service not in self.circuits:
            self.circuits[service] = CircuitState.CLOSED
        return self.circuits[service]

    def _set_state(self, service: str, new_state: CircuitState):
        """Change circuit state"""
        old_state = self._get_state(service)
        if old_state != new_state:
            logger.info(f"Circuit for '{service}': {old_state.value} -> {new_state.value}")
            self.circuits[service] = new_state
            self.metrics[service].state_changes += 1

            if new_state == CircuitState.OPEN:
                self.opened_at[service] = time.time()

    def _calculate_adaptive_timeout(self, service: str) -> float:
        """Calculate timeout based on historical recovery patterns"""
        if not self.enable_adaptive_timeout:
            return self.base_timeout

        if service not in self.adaptive_timeouts:
            return self.base_timeout

        # If we've learned from past recoveries, use that
        learned_timeout = self.adaptive_timeouts[service]

        # Gradually increase timeout if service keeps failing
        metrics = self._get_metrics(service)
        if metrics.state_changes > 5:  # Been flapping
            return min(learned_timeout * 1.5, 300.0)  # Max 5 minutes

        return learned_timeout

    def _should_attempt_reset(self, service: str) -> bool:
        """Check if enough time has passed to try half-open"""
        if service not in self.opened_at:
            return False

        elapsed = time.time() - self.opened_at[service]
        timeout = self._calculate_adaptive_timeout(service)

        return elapsed >= timeout

    def _on_success(self, service: str):
        """Handle successful call"""
        lock = self._get_lock(service)
        with lock:
            metrics = self._get_metrics(service)
            state = self._get_state(service)

            metrics.total_calls += 1
            metrics.successful_calls += 1
            metrics.consecutive_successes += 1
            metrics.consecutive_failures = 0
            metrics.last_success_time = time.time()
            metrics.recent_results.append(True)

            if state == CircuitState.HALF_OPEN:
                # Track recovery time for adaptive timeout
                if service in self.opened_at:
                    recovery_time = time.time() - self.opened_at[service]
                    # Learn from this recovery
                    if service not in self.adaptive_timeouts:
                        self.adaptive_timeouts[service] = recovery_time
                    else:
                        # Exponential moving average
                        current = self.adaptive_timeouts[service]
                        self.adaptive_timeouts[service] = 0.7 * current + 0.3 * recovery_time

                # Check if we can close the circuit
                if metrics.consecutive_successes >= self.success_threshold:
                    self._set_state(service, CircuitState.CLOSED)
                    logger.info(
                        f"Circuit for '{service}' closed after {metrics.consecutive_successes} "
                        f"successful attempts"
                    )

            self._save_state()

    def _on_failure(self, service: str, error: Exception):
        """Handle failed call"""
        lock = self._get_lock(service)
        with lock:
            metrics = self._get_metrics(service)
            state = self._get_state(service)

            metrics.total_calls += 1
            metrics.failed_calls += 1
            metrics.consecutive_failures += 1
            metrics.consecutive_successes = 0
            metrics.last_failure_time = time.time()
            metrics.recent_results.append(False)

            # Check if we should open the circuit
            should_open = False

            # Check consecutive failures
            if metrics.consecutive_failures >= self.failure_threshold:
                should_open = True
                reason = f"consecutive failures ({metrics.consecutive_failures})"

            # Check failure rate in rolling window
            elif len(metrics.recent_results) >= 10:  # Need minimum data
                failure_rate = metrics.get_failure_rate()
                if failure_rate >= self.failure_rate_threshold:
                    should_open = True
                    reason = f"high failure rate ({failure_rate:.1%})"

            if should_open and state != CircuitState.OPEN:
                self._set_state(service, CircuitState.OPEN)
                logger.warning(
                    f"Circuit for '{service}' opened due to {reason}. "
                    f"Error: {error}"
                )

            # If we were in half-open and failed, go back to open
            elif state == CircuitState.HALF_OPEN:
                self._set_state(service, CircuitState.OPEN)
                logger.warning(
                    f"Circuit for '{service}' reopened after failure in half-open state"
                )

            self._save_state()

    def call(
        self,
        operation: Callable[[], T],
        service: str,
        fallback: Optional[Callable[[], T]] = None,
    ) -> T:
        """
        Execute operation with circuit breaker protection.

        Args:
            operation: The function to execute
            service: Service identifier (e.g., "gemini", "claude")
            fallback: Optional fallback function if circuit is open

        Returns:
            Result from operation or fallback

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallback provided
            Exception: From operation if it fails
        """
        lock = self._get_lock(service)

        # Check state (thread-safe read)
        with lock:
            state = self._get_state(service)

            # If OPEN, check if we should transition to HALF_OPEN
            if state == CircuitState.OPEN:
                if self._should_attempt_reset(service):
                    self._set_state(service, CircuitState.HALF_OPEN)
                    logger.info(f"Circuit for '{service}' transitioning to half-open")
                    state = CircuitState.HALF_OPEN
                else:
                    # Still open, fail fast
                    if fallback:
                        logger.warning(
                            f"Circuit for '{service}' is OPEN, using fallback"
                        )
                        return fallback()
                    else:
                        raise CircuitBreakerOpenError(
                            f"Circuit breaker is OPEN for service '{service}'. "
                            f"Service is temporarily unavailable."
                        )

        # Execute operation
        try:
            result = operation()
            self._on_success(service)
            return result
        except Exception as e:
            self._on_failure(service, e)

            # If we have fallback, use it
            if fallback:
                logger.warning(
                    f"Operation failed for '{service}', using fallback. Error: {e}"
                )
                return fallback()

            # Otherwise re-raise
            raise

    def get_state(self, service: str) -> CircuitState:
        """Get current state of a service's circuit"""
        return self._get_state(service)

    def is_available(self, service: str) -> bool:
        """Check if service is available (not OPEN)"""
        state = self._get_state(service)
        return state != CircuitState.OPEN

    def reset(self, service: str):
        """Manually reset a circuit to CLOSED state"""
        lock = self._get_lock(service)
        with lock:
            self._set_state(service, CircuitState.CLOSED)
            metrics = self._get_metrics(service)
            metrics.consecutive_failures = 0
            metrics.consecutive_successes = 0
            logger.info(f"Circuit for '{service}' manually reset to CLOSED")
            self._save_state()

    def get_metrics(self, service: str) -> dict[str, Any]:
        """Get metrics for a service"""
        metrics = self._get_metrics(service)
        state = self._get_state(service)

        return {
            "service": service,
            "state": state.value,
            "total_calls": metrics.total_calls,
            "successful_calls": metrics.successful_calls,
            "failed_calls": metrics.failed_calls,
            "success_rate": metrics.get_success_rate(),
            "failure_rate": metrics.get_failure_rate(),
            "consecutive_failures": metrics.consecutive_failures,
            "consecutive_successes": metrics.consecutive_successes,
            "state_changes": metrics.state_changes,
            "adaptive_timeout": self.adaptive_timeouts.get(service, self.base_timeout),
        }

    def get_all_services(self) -> list[str]:
        """Get list of all tracked services"""
        return list(self.circuits.keys())

    def _save_state(self):
        """Persist circuit state to disk"""
        state_file = self.cache_dir / "circuit_state.json"
        try:
            state = {
                "circuits": {
                    service: state.value for service, state in self.circuits.items()
                },
                "adaptive_timeouts": self.adaptive_timeouts,
                "opened_at": self.opened_at,
            }
            with state_file.open("w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save circuit state: {e}")

    def _load_state(self):
        """Load persisted circuit state from disk"""
        state_file = self.cache_dir / "circuit_state.json"
        if not state_file.exists():
            return

        try:
            with state_file.open("r") as f:
                state = json.load(f)

            # Restore circuits (but always start in CLOSED on restart)
            for service in state.get("circuits", {}).keys():
                self.circuits[service] = CircuitState.CLOSED

            # Restore learned timeouts
            self.adaptive_timeouts = state.get("adaptive_timeouts", {})

            logger.info(f"Loaded circuit state for {len(self.circuits)} services")
        except Exception as e:
            logger.warning(f"Failed to load circuit state: {e}")


# Global circuit breaker instance
_global_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker instance (singleton)"""
    global _global_circuit_breaker
    if _global_circuit_breaker is None:
        _global_circuit_breaker = CircuitBreaker()
    return _global_circuit_breaker
