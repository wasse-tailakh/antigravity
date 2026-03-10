"""
Enhanced Executor with All Advanced Algorithms Integrated

This is an improved version of executor.py that integrates:
- Circuit Breaker for resilience
- Adaptive Backoff for smart retries
- Smart Priority Queue for intelligent scheduling
- Quality Scorer for response validation
- Smart Cache for cost optimization
"""

import os
from typing import Any, Dict, List

from orchestrator.planner import Planner
from agents.router_agent import RouterAgent
from tools.tool_registry import ToolRegistry
from skills.file_skill import FileSkill
from skills.shell_skill import ShellSkill
from skills.git_skill import GitSkill
from config.logger import get_logger

# Import advanced algorithms
from orchestrator.adaptive_backoff import AdaptiveBackoff
from orchestrator.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from orchestrator.smart_priority_queue import SmartPriorityQueue, TaskPriority, TaskStatus
from orchestrator.quality_scorer import ResponseQualityScorer, QualityLevel
from memory.smart_cache import SmartCache
from policies.cost_guard import CostGuard


class EnhancedExecutor:
    """
    Production-ready executor with advanced reliability and optimization.

    Improvements over original Executor:
    1. Circuit breaker prevents cascading failures
    2. Adaptive backoff learns optimal retry strategies
    3. Smart priority queue optimizes execution order
    4. Quality scorer validates responses
    5. Smart cache minimizes redundant LLM calls
    """

    def __init__(self):
        self.logger = get_logger("EnhancedExecutor")

        # Original components
        self.planner = Planner()
        self.router = RouterAgent()
        self.cost_guard = CostGuard()

        # Tool Registry
        self.tool_registry = ToolRegistry()
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.tool_registry.register(FileSkill(project_root=project_root))
        self.tool_registry.register(ShellSkill())
        self.tool_registry.register(GitSkill())

        # Advanced components
        self.backoff = AdaptiveBackoff(enable_learning=True)
        self.circuit_breaker = get_circuit_breaker()
        self.priority_queue = SmartPriorityQueue(
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

        self.logger.info("Enhanced Executor initialized with advanced algorithms")

    def _execute_agent_with_resilience(
        self,
        agent_name: str,
        prompt: str,
        context: Dict[str, Any] = None,
    ) -> str:
        """
        Execute agent with full resilience stack.

        Layers:
        1. Smart cache (avoid redundant calls)
        2. Circuit breaker (fail fast if agent is down)
        3. Adaptive backoff (smart retries)
        4. Quality scoring (validate response)
        """

        # Create cache key
        cache_key = {
            "agent": agent_name,
            "prompt": prompt[:100],  # Truncate for cache key
            "context_hash": hash(str(context)),
        }

        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.logger.info(f"Cache HIT for {agent_name}")
            return cached_result["response"]

        self.logger.info(f"Cache MISS for {agent_name}, executing...")

        # Define the agent operation
        def agent_operation():
            # Get agent
            if agent_name in self.router.agents:
                agent = self.router.agents[agent_name]
            else:
                agent = self.router

            # Execute with tools
            return agent.run(
                prompt=prompt,
                context=context,
                tools_registry=self.tool_registry,
            )

        # Wrap with adaptive backoff
        def resilient_call():
            return self.backoff.execute_with_adaptive_backoff(
                operation=agent_operation,
                provider=agent_name,
                max_attempts=3,
            )

        # Execute with circuit breaker
        try:
            response = self.circuit_breaker.call(
                operation=resilient_call,
                service=agent_name,
            )
        except CircuitBreakerOpenError:
            # Circuit is open, fallback to gemini
            self.logger.warning(
                f"Circuit open for {agent_name}, falling back to gemini"
            )
            if agent_name != "gemini":
                response = self.backoff.execute_with_adaptive_backoff(
                    operation=lambda: self.router.agents["gemini"].run(
                        prompt, context, self.tool_registry
                    ),
                    provider="gemini",
                    max_attempts=2,
                )
            else:
                raise Exception(f"All agents unavailable")

        # Score quality
        quality = self.quality_scorer.score_response(
            response=response,
            request=prompt,
        )

        self.logger.info(
            f"Response quality: {quality.level.value} ({quality.overall_score:.1f}/100)"
        )

        # If quality is poor, retry once
        if quality.needs_retry():
            self.logger.warning("Poor quality response, retrying...")
            try:
                response = resilient_call()
                # Re-score
                quality = self.quality_scorer.score_response(
                    response=response,
                    request=prompt,
                )
            except Exception as e:
                self.logger.error(f"Retry failed: {e}")

        # Cache if quality is acceptable
        if quality.is_acceptable():
            # Estimate cost based on agent
            cost_map = {"claude": 5.0, "openai": 3.0, "gemini": 1.0}
            cost = cost_map.get(agent_name, 1.0)

            self.cache.set(
                key=cache_key,
                value={
                    "response": response,
                    "quality_score": quality.overall_score,
                },
                cost=cost,
                tags={agent_name, "execution"},
            )
            self.logger.info(f"Cached response (cost={cost})")

        return response

    def execute_task(self, user_request: str) -> List[Dict[str, Any]]:
        """
        Execute task with intelligent scheduling and resilience.

        Improvements:
        1. Plans are cached
        2. Steps are enqueued to priority queue
        3. Execution order is optimized
        4. Each step uses resilience stack
        5. Dependencies are handled automatically
        """

        self.logger.info(f"New Task Received: {user_request}")

        # 1. Planning Phase (with caching)
        try:
            plan = self.cache.get_or_compute(
                key=f"plan:{user_request}",
                compute_fn=lambda: self.planner.create_plan(user_request),
                cost=3.0,  # Planning is moderately expensive
                tags={"planning"},
                ttl=7200,  # 2 hours
            )
        except Exception as e:
            self.logger.critical(f"Planner failed critically: {e}", exc_info=True)
            return []

        self.logger.info("--- Execution Plan ---")
        for step in plan:
            self.logger.info(
                f"Step {step.get('id', '?')}: {step.get('description', 'Unknown')} "
                f"(Agent: {step.get('agent_type', 'router')})"
            )

        # 2. Enqueue all steps to priority queue
        for i, step in enumerate(plan):
            step_id = f"step_{step.get('id', i)}"
            desc = step.get('description', '')
            agent_type = step.get('agent_type', 'gemini').lower()

            # Determine priority based on step characteristics
            if 'critical' in desc.lower() or 'urgent' in desc.lower():
                priority = TaskPriority.CRITICAL
            elif 'important' in desc.lower() or i == 0:  # First step is important
                priority = TaskPriority.HIGH
            elif 'optional' in desc.lower() or 'cleanup' in desc.lower():
                priority = TaskPriority.LOW
            else:
                priority = TaskPriority.NORMAL

            # Estimate cost
            cost_map = {"claude": 5.0, "openai": 3.0, "gemini": 1.0}
            estimated_cost = cost_map.get(agent_type, 1.0)

            # Extract dependencies (if previous steps must complete first)
            dependencies = set()
            if i > 0 and 'independent' not in desc.lower():
                # By default, depend on previous step
                dependencies.add(f"step_{plan[i-1].get('id', i-1)}")

            self.priority_queue.enqueue(
                task_id=step_id,
                payload=step,
                priority=priority,
                description=desc,
                estimated_cost=estimated_cost,
                dependencies=dependencies,
                tags={agent_type, "execution"},
                preferred_agent=agent_type,
            )

        self.logger.info(f"Enqueued {len(plan)} steps to priority queue")
        self.logger.info(f"Queue status: {self.priority_queue.get_status()}")

        # 3. Execute in optimal order
        self.cost_guard.reset()
        final_results = []

        while not self.priority_queue.is_empty():
            # Get highest priority ready task
            dequeued = self.priority_queue.dequeue(skip_blocked=True)

            if dequeued is None:
                self.logger.warning("No ready tasks, but queue not empty (circular dependency?)")
                break

            step_id, step_payload, metadata = dequeued

            self.logger.info(
                f"Executing {step_id}: {metadata.description} "
                f"(priority={metadata.base_priority}, attempt={metadata.retry_count + 1})"
            )

            try:
                # Cost guard check
                if not self.cost_guard.log_llm_call():
                    self.logger.error("CostGuard threshold exceeded, halting")
                    self.priority_queue.mark_failed(step_id, retry=False)
                    final_results.append({
                        "step_id": step_id,
                        "status": "failed",
                        "error": "CostGuard threshold exceeded",
                    })
                    break

                # Execute with full resilience stack
                agent_name = metadata.preferred_agent or "gemini"
                desc = metadata.description

                agent_output = self._execute_agent_with_resilience(
                    agent_name=agent_name,
                    prompt=desc,
                    context={"step": desc},
                )

                # Mark as completed
                self.priority_queue.mark_completed(step_id, success=True)

                self.logger.info(f"Step {step_id} completed successfully")

                final_results.append({
                    "step_id": step_id,
                    "description": desc,
                    "status": "completed",
                    "output": agent_output,
                    "agent": agent_name,
                    "attempts": metadata.retry_count + 1,
                })

            except Exception as e:
                self.logger.error(
                    f"Step {step_id} failed: {e}",
                    exc_info=True
                )

                # Mark as failed (will retry if allowed)
                self.priority_queue.mark_failed(step_id, retry=True)

                final_results.append({
                    "step_id": step_id,
                    "description": metadata.description,
                    "status": "failed",
                    "error": str(e),
                    "attempts": metadata.retry_count + 1,
                })

                # Check if we should halt
                if 'critical' in metadata.description.lower():
                    self.logger.error(f"Critical step {step_id} failed, halting execution")
                    break

        # 4. Generate execution report
        self.logger.info("Execution Complete.")

        # Log statistics
        stats = self._get_execution_stats()
        self.logger.info("=== Execution Statistics ===")
        self.logger.info(f"Cache Hit Rate: {stats['cache']['hit_rate']:.1%}")
        self.logger.info(f"Total Completed: {stats['queue']['completed']}")
        self.logger.info(f"Circuit Breakers: {stats['circuit_status']}")

        return final_results

    def _get_execution_stats(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics"""
        cache_stats = self.cache.get_stats()
        queue_stats = self.priority_queue.get_status()

        # Circuit breaker status
        circuit_status = {}
        for service in ["gemini", "claude", "openai"]:
            if self.circuit_breaker.is_available(service):
                circuit_status[service] = "available"
            else:
                circuit_status[service] = "unavailable"

        return {
            "cache": cache_stats,
            "queue": queue_stats,
            "circuit_status": circuit_status,
            "backoff_stats": {
                provider: self.backoff.get_provider_stats(provider)
                for provider in ["gemini", "claude", "openai"]
                if provider in self.backoff.provider_metrics
            },
        }

    def print_detailed_stats(self):
        """Print detailed statistics to console"""
        stats = self._get_execution_stats()

        print("\n" + "=" * 60)
        print("📊 EXECUTION STATISTICS")
        print("=" * 60)

        print("\n💾 Cache:")
        print(f"  Hit Rate: {stats['cache']['hit_rate']:.1%}")
        print(f"  Size: {stats['cache']['size']}/{stats['cache']['max_size']}")
        print(f"  Memory: {stats['cache']['memory_mb']:.1f} MB")

        print("\n📋 Queue:")
        print(f"  Completed: {stats['queue']['completed']}")
        print(f"  Running: {stats['queue']['running']}")

        print("\n⚡ Circuit Breakers:")
        for service, status in stats['circuit_status'].items():
            icon = "✅" if status == "available" else "❌"
            print(f"  {icon} {service}: {status}")

        print("\n🔄 Backoff Learning:")
        for provider, metrics in stats.get('backoff_stats', {}).items():
            print(f"  {provider}:")
            print(f"    Success Rate: {metrics.get('success_rate', 0):.1%}")
            print(f"    Optimal Delay: {metrics.get('optimal_delay', 0):.2f}s")

        print("=" * 60 + "\n")


# Example usage
if __name__ == "__main__":
    executor = EnhancedExecutor()

    # Example 1: Simple task
    print("\n🚀 Example 1: Simple Analysis Task")
    results = executor.execute_task(
        "Analyze the README.md file and suggest 3 improvements."
    )

    for result in results:
        print(f"✓ {result['step_id']}: {result['status']}")

    # Print stats
    executor.print_detailed_stats()

    # Example 2: Complex multi-step task
    print("\n🚀 Example 2: Complex Multi-Step Task")
    results = executor.execute_task(
        "Create a plan for building a todo app, then implement the backend API "
        "and write comprehensive tests. Make sure to include error handling."
    )

    for result in results:
        status_icon = "✓" if result['status'] == 'completed' else "✗"
        print(f"{status_icon} {result['step_id']}: {result['status']}")

    # Print final stats
    executor.print_detailed_stats()
