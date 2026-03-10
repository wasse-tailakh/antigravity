"""
Demo: Advanced Multi-Agent System with All Algorithms

This demonstrates how all 5 advanced algorithms work together
to create a highly resilient, efficient, and intelligent system.
"""

import time
from typing import Any, Dict

from orchestrator.adaptive_backoff import AdaptiveBackoff
from orchestrator.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from orchestrator.smart_priority_queue import SmartPriorityQueue, TaskPriority
from orchestrator.quality_scorer import ResponseQualityScorer
from memory.smart_cache import SmartCache
from config.logger import get_logger

logger = get_logger("AdvancedDemo")


class AdvancedAgentOrchestrator:
    """
    Production-ready orchestrator combining all advanced algorithms.

    Features:
    - Resilient API calls with circuit breaker and adaptive backoff
    - Intelligent task scheduling with priority queue
    - Quality-based response validation
    - Smart caching to minimize costs
    """

    def __init__(self):
        # Initialize all components
        self.backoff = AdaptiveBackoff(enable_learning=True)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=30.0,
            enable_adaptive_timeout=True,
        )
        self.task_queue = SmartPriorityQueue(
            max_size=1000,
            enable_aging=True,
            enable_cost_optimization=True,
            enable_learning=True,
        )
        self.quality_scorer = ResponseQualityScorer()
        self.cache = SmartCache(
            max_size=500,
            max_memory_mb=100,
            enable_adaptive_ttl=True,
        )

        logger.info("Advanced orchestrator initialized with all algorithms")

    def execute_with_resilience(
        self,
        operation: callable,
        provider: str,
        fallback_provider: str = None,
    ) -> Any:
        """
        Execute LLM call with full resilience stack.

        Combines:
        1. Circuit Breaker (fail fast if provider is down)
        2. Adaptive Backoff (smart retries)
        3. Fallback to alternative provider
        """

        def resilient_call():
            # Adaptive backoff wraps the actual call
            return self.backoff.execute_with_adaptive_backoff(
                operation=operation,
                provider=provider,
                max_attempts=3,
            )

        try:
            # Circuit breaker protects from repeated failures
            result = self.circuit_breaker.call(
                operation=resilient_call,
                service=provider,
            )
            return result

        except CircuitBreakerOpenError:
            logger.warning(
                f"Circuit open for {provider}, "
                f"attempting fallback to {fallback_provider}"
            )

            if fallback_provider:
                # Fallback to alternative provider
                return self.backoff.execute_with_adaptive_backoff(
                    operation=operation,
                    provider=fallback_provider,
                    max_attempts=2,
                )
            raise

    def cached_llm_call(
        self,
        prompt: str,
        provider: str,
        expected_format: str = None,
        cost: float = 1.0,
        ttl: float = None,
    ) -> Dict[str, Any]:
        """
        LLM call with smart caching and quality scoring.

        Flow:
        1. Check cache
        2. If miss, call LLM with resilience
        3. Score quality
        4. If good, cache result
        5. If poor, retry once
        """

        # Create cache key
        cache_key = {
            "prompt": prompt,
            "provider": provider,
            "format": expected_format,
        }

        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache HIT for {provider} call")
            return cached_result

        logger.info(f"Cache MISS for {provider} call")

        # Define the LLM operation
        def llm_operation():
            # This would call your actual agent
            # For demo, we'll simulate
            logger.info(f"Calling {provider}...")
            time.sleep(0.5)  # Simulate API call
            return f"Response from {provider} for: {prompt[:50]}..."

        # Execute with full resilience
        response = self.execute_with_resilience(
            operation=llm_operation,
            provider=provider,
            fallback_provider="gemini" if provider != "gemini" else None,
        )

        # Score quality
        quality_score = self.quality_scorer.score_response(
            response=response,
            request=prompt,
            expected_format=expected_format,
        )

        logger.info(
            f"Response quality: {quality_score.level.value} "
            f"({quality_score.overall_score:.1f}/100)"
        )

        # If quality is too poor, retry once
        if quality_score.needs_retry():
            logger.warning("Poor quality response, retrying...")
            response = self.execute_with_resilience(
                operation=llm_operation,
                provider=provider,
                fallback_provider="gemini",
            )
            # Re-score
            quality_score = self.quality_scorer.score_response(
                response=response,
                request=prompt,
                expected_format=expected_format,
            )

        # Cache if acceptable quality
        if quality_score.is_acceptable():
            self.cache.set(
                key=cache_key,
                value={
                    "response": response,
                    "quality_score": quality_score.overall_score,
                    "provider": provider,
                },
                cost=cost,
                ttl=ttl,
                tags={provider, expected_format} if expected_format else {provider},
            )

        return {
            "response": response,
            "quality_score": quality_score.overall_score,
            "provider": provider,
        }

    def intelligent_task_execution(self, tasks: list[Dict]) -> list[Dict]:
        """
        Execute multiple tasks with intelligent scheduling.

        Uses SmartPriorityQueue to:
        1. Optimize execution order
        2. Handle dependencies
        3. Prevent starvation
        4. Learn from patterns
        """

        # Enqueue all tasks
        for task in tasks:
            self.task_queue.enqueue(
                task_id=task["id"],
                payload=task,
                priority=task.get("priority", TaskPriority.NORMAL),
                description=task.get("description", ""),
                estimated_cost=task.get("cost", 1.0),
                dependencies=set(task.get("dependencies", [])),
                tags=set(task.get("tags", [])),
                preferred_agent=task.get("agent", "gemini"),
            )

        logger.info(f"Enqueued {len(tasks)} tasks")
        logger.info(f"Queue status: {self.task_queue.get_status()}")

        # Execute in optimal order
        results = []
        while not self.task_queue.is_empty():
            task_id, payload, metadata = self.task_queue.dequeue()

            logger.info(f"Executing task {task_id}: {metadata.description}")

            try:
                # Execute task with caching and quality checks
                result = self.cached_llm_call(
                    prompt=payload.get("prompt", ""),
                    provider=metadata.preferred_agent or "gemini",
                    cost=metadata.estimated_cost,
                )

                # Mark as completed
                self.task_queue.mark_completed(task_id, success=True)

                results.append({
                    "task_id": task_id,
                    "status": "completed",
                    "result": result,
                })

            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")

                # Mark as failed (will retry if allowed)
                self.task_queue.mark_failed(task_id, retry=True)

                results.append({
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e),
                })

        return results

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            "cache": self.cache.get_stats(),
            "queue": self.task_queue.get_status(),
            "circuit_breaker": {
                service: self.circuit_breaker.get_metrics(service)
                for service in self.circuit_breaker.get_all_services()
            },
            "backoff": {
                provider: self.backoff.get_provider_stats(provider)
                for provider in ["gemini", "claude", "openai"]
                if provider in self.backoff.provider_metrics
            },
        }


def demo_basic_usage():
    """Demo 1: Basic resilient LLM call"""
    print("\n" + "=" * 60)
    print("DEMO 1: Basic Resilient LLM Call")
    print("=" * 60)

    orchestrator = AdvancedAgentOrchestrator()

    result = orchestrator.cached_llm_call(
        prompt="Explain what is a REST API",
        provider="gemini",
        expected_format="markdown",
        cost=1.0,
    )

    print(f"\nResult: {result['response'][:100]}...")
    print(f"Quality Score: {result['quality_score']:.1f}/100")


def demo_priority_queue():
    """Demo 2: Intelligent task scheduling"""
    print("\n" + "=" * 60)
    print("DEMO 2: Intelligent Task Scheduling")
    print("=" * 60)

    orchestrator = AdvancedAgentOrchestrator()

    tasks = [
        {
            "id": "task_1",
            "description": "Analyze codebase",
            "prompt": "Analyze the main codebase structure",
            "priority": TaskPriority.NORMAL,
            "cost": 2.0,
            "agent": "gemini",
            "tags": ["analysis"],
        },
        {
            "id": "task_2",
            "description": "Generate report (URGENT)",
            "prompt": "Generate security report",
            "priority": TaskPriority.CRITICAL,
            "cost": 5.0,
            "agent": "claude",
            "tags": ["report", "urgent"],
        },
        {
            "id": "task_3",
            "description": "Update documentation",
            "prompt": "Update README",
            "priority": TaskPriority.LOW,
            "cost": 1.0,
            "agent": "gemini",
            "tags": ["docs"],
            "dependencies": ["task_1"],  # Waits for task_1
        },
    ]

    results = orchestrator.intelligent_task_execution(tasks)

    print("\n--- Execution Results ---")
    for result in results:
        print(f"Task {result['task_id']}: {result['status']}")


def demo_resilience():
    """Demo 3: Resilience under failures"""
    print("\n" + "=" * 60)
    print("DEMO 3: Resilience Under Failures")
    print("=" * 60)

    orchestrator = AdvancedAgentOrchestrator()

    # Simulate multiple calls (some will fail)
    for i in range(10):
        try:
            def flaky_operation():
                import random
                if random.random() < 0.3:  # 30% failure rate
                    raise Exception("API rate limit exceeded")
                return f"Success response {i}"

            result = orchestrator.execute_with_resilience(
                operation=flaky_operation,
                provider="test_provider",
            )
            print(f"Call {i}: ✓ {result}")

        except Exception as e:
            print(f"Call {i}: ✗ {e}")

    # Show learned metrics
    stats = orchestrator.backoff.get_provider_stats("test_provider")
    print(f"\n--- Provider Stats ---")
    print(f"Success Rate: {stats.get('success_rate', 0):.1%}")
    print(f"Optimal Delay: {stats.get('optimal_delay', 0):.2f}s")


def demo_comprehensive():
    """Demo 4: Full system with all algorithms"""
    print("\n" + "=" * 60)
    print("DEMO 4: Comprehensive System Demo")
    print("=" * 60)

    orchestrator = AdvancedAgentOrchestrator()

    # Complex workflow
    tasks = [
        {
            "id": "plan",
            "description": "Create execution plan",
            "prompt": "Plan how to build a todo app",
            "priority": TaskPriority.HIGH,
            "cost": 3.0,
            "agent": "claude",
        },
        {
            "id": "implement_backend",
            "description": "Implement backend",
            "prompt": "Write Flask API for todo app",
            "priority": TaskPriority.NORMAL,
            "cost": 2.0,
            "agent": "gemini",
            "dependencies": ["plan"],
        },
        {
            "id": "implement_frontend",
            "description": "Implement frontend",
            "prompt": "Write React frontend for todo app",
            "priority": TaskPriority.NORMAL,
            "cost": 2.0,
            "agent": "gemini",
            "dependencies": ["plan"],
        },
        {
            "id": "testing",
            "description": "Write tests",
            "prompt": "Write comprehensive tests",
            "priority": TaskPriority.HIGH,
            "cost": 1.5,
            "agent": "gemini",
            "dependencies": ["implement_backend", "implement_frontend"],
        },
    ]

    results = orchestrator.intelligent_task_execution(tasks)

    # Show comprehensive stats
    print("\n--- System Statistics ---")
    stats = orchestrator.get_system_stats()

    print(f"\nCache: Hit Rate = {stats['cache']['hit_rate']:.1%}")
    print(f"Queue: Completed = {stats['queue']['completed']}")

    print("\nCircuit Breakers:")
    for service, metrics in stats.get('circuit_breaker', {}).items():
        print(f"  {service}: {metrics['state']} "
              f"(Success Rate: {metrics['success_rate']:.1%})")


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("Advanced Multi-Agent System - Full Demo")
    print("🚀 " * 20)

    # Run all demos
    demo_basic_usage()
    demo_priority_queue()
    demo_resilience()
    demo_comprehensive()

    print("\n" + "✅ " * 20)
    print("All demos completed successfully!")
    print("✅ " * 20 + "\n")
