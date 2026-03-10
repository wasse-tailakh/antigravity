"""
Intelligent Task Priority Queue with Dynamic Prioritization

Features:
- Multi-factor priority scoring
- Deadline-aware scheduling
- Cost-based optimization
- Dependency resolution
- Starvation prevention
- Learning from execution patterns
"""

from __future__ import annotations

import heapq
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, Set
from pathlib import Path
import json

from config.logger import get_logger

logger = get_logger("SmartPriorityQueue")


class TaskPriority(Enum):
    """Base priority levels"""
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 10


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Waiting on dependencies


@dataclass
class TaskMetadata:
    """Metadata for intelligent scheduling"""
    task_id: str
    description: str
    base_priority: int
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None  # Unix timestamp
    estimated_cost: float = 1.0  # Estimated LLM cost (1.0 = baseline)
    estimated_duration: float = 30.0  # Seconds
    dependencies: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    retry_count: int = 0
    max_retries: int = 3
    preferred_agent: Optional[str] = None  # gemini, claude, openai
    status: TaskStatus = TaskStatus.PENDING

    # Dynamic priority boosting
    starvation_threshold: float = 300.0  # 5 minutes
    aging_factor: float = 0.1  # Priority increase per minute

    def __post_init__(self):
        """Ensure dependencies is a set"""
        if not isinstance(self.dependencies, set):
            self.dependencies = set(self.dependencies) if self.dependencies else set()
        if not isinstance(self.tags, set):
            self.tags = set(self.tags) if self.tags else set()


@dataclass(order=True)
class PrioritizedTask:
    """Wrapper for tasks in priority queue"""
    # Negative priority for max-heap behavior (higher priority = first out)
    priority: float = field(compare=True)
    task_id: str = field(compare=False)
    metadata: TaskMetadata = field(compare=False)
    payload: Any = field(compare=False)


class SmartPriorityQueue:
    """
    Intelligent task scheduler with multi-dimensional prioritization.

    Priority calculation considers:
    1. Base priority (user-defined importance)
    2. Deadline urgency (time-sensitive tasks)
    3. Cost efficiency (optimize resource usage)
    4. Aging (prevent starvation)
    5. Dependencies (unblock dependent tasks)
    6. Historical performance (learn from past executions)
    """

    def __init__(
        self,
        enable_aging: bool = True,
        enable_cost_optimization: bool = True,
        enable_learning: bool = True,
        cache_dir: str | Path = ".cache/task_queue",
    ):
        self.enable_aging = enable_aging
        self.enable_cost_optimization = enable_cost_optimization
        self.enable_learning = enable_learning
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Priority queue (heap)
        self.queue: list[PrioritizedTask] = []
        self.tasks: dict[str, PrioritizedTask] = {}  # Fast lookup

        # Dependency tracking
        self.dependency_graph: dict[str, Set[str]] = {}  # task_id -> dependents
        self.completed_tasks: Set[str] = set()
        self.running_tasks: Set[str] = set()

        # Learning: track execution patterns
        self.execution_history: dict[str, list[dict]] = {}  # tag -> history

        # Thread safety
        self.lock = threading.Lock()

        # Load historical data
        self._load_history()

    def _calculate_dynamic_priority(self, metadata: TaskMetadata) -> float:
        """
        Calculate dynamic priority score using multiple factors.

        Higher score = higher priority (more urgent/important)
        """
        priority = float(metadata.base_priority)

        # 1. Deadline urgency factor
        if metadata.deadline:
            time_until_deadline = metadata.deadline - time.time()
            if time_until_deadline <= 0:
                # Past deadline! Maximum urgency boost
                priority += 200
            elif time_until_deadline < 60:  # Less than 1 minute
                priority += 100
            elif time_until_deadline < 300:  # Less than 5 minutes
                priority += 50
            elif time_until_deadline < 900:  # Less than 15 minutes
                priority += 25
            else:
                # Add small boost based on approaching deadline
                deadline_factor = max(0, 1.0 - (time_until_deadline / 3600))
                priority += deadline_factor * 20

        # 2. Aging factor (prevent starvation)
        if self.enable_aging:
            age_seconds = time.time() - metadata.created_at
            if age_seconds > metadata.starvation_threshold:
                # Task is getting old, boost priority
                minutes_old = age_seconds / 60
                aging_boost = minutes_old * metadata.aging_factor
                priority += aging_boost

        # 3. Cost efficiency factor
        if self.enable_cost_optimization:
            # Prefer cheaper tasks when priorities are similar
            # This creates "cost tiers" within priority levels
            cost_penalty = metadata.estimated_cost * 2
            priority -= cost_penalty

        # 4. Dependency factor
        # Boost tasks that would unblock other tasks
        if metadata.task_id in self.dependency_graph:
            num_dependents = len(self.dependency_graph[metadata.task_id])
            if num_dependents > 0:
                # Each dependent adds a small boost
                priority += num_dependents * 5

        # 5. Retry penalty
        # Penalize tasks that have failed before (but still allow retries)
        if metadata.retry_count > 0:
            retry_penalty = metadata.retry_count * 10
            priority -= retry_penalty

        # 6. Learning factor (from historical data)
        if self.enable_learning and metadata.tags:
            for tag in metadata.tags:
                if tag in self.execution_history:
                    history = self.execution_history[tag]
                    # If this type of task often fails, deprioritize slightly
                    recent_failures = sum(
                        1 for h in history[-10:] if h.get("success") is False
                    )
                    if recent_failures > 5:  # More than 50% failure rate
                        priority -= 15

        return priority

    def _is_task_ready(self, metadata: TaskMetadata) -> bool:
        """Check if task's dependencies are satisfied"""
        if not metadata.dependencies:
            return True

        # All dependencies must be completed
        return metadata.dependencies.issubset(self.completed_tasks)

    def _update_dependency_graph(self, task_id: str, dependencies: Set[str]):
        """Update reverse dependency graph"""
        for dep_id in dependencies:
            if dep_id not in self.dependency_graph:
                self.dependency_graph[dep_id] = set()
            self.dependency_graph[dep_id].add(task_id)

    def enqueue(
        self,
        task_id: str,
        payload: Any,
        priority: TaskPriority | int = TaskPriority.NORMAL,
        description: str = "",
        deadline: Optional[datetime | float] = None,
        estimated_cost: float = 1.0,
        estimated_duration: float = 30.0,
        dependencies: Optional[Set[str]] = None,
        tags: Optional[Set[str]] = None,
        preferred_agent: Optional[str] = None,
    ) -> bool:
        """
        Add a task to the queue.

        Args:
            task_id: Unique identifier
            payload: Task data/function
            priority: Base priority (enum or int)
            description: Human-readable description
            deadline: When task must complete (datetime or unix timestamp)
            estimated_cost: Relative LLM cost (1.0 = baseline)
            estimated_duration: Expected execution time in seconds
            dependencies: Set of task_ids this task depends on
            tags: Task classification tags for learning
            preferred_agent: Preferred agent (gemini/claude/openai)

        Returns:
            True if enqueued, False if duplicate
        """
        with self.lock:
            # Check for duplicates
            if task_id in self.tasks:
                logger.warning(f"Task {task_id} already in queue, skipping")
                return False

            # Convert priority enum to int
            base_priority = priority.value if isinstance(priority, TaskPriority) else priority

            # Convert deadline to timestamp
            deadline_ts = None
            if isinstance(deadline, datetime):
                deadline_ts = deadline.timestamp()
            elif isinstance(deadline, (int, float)):
                deadline_ts = float(deadline)

            # Create metadata
            metadata = TaskMetadata(
                task_id=task_id,
                description=description,
                base_priority=base_priority,
                deadline=deadline_ts,
                estimated_cost=estimated_cost,
                estimated_duration=estimated_duration,
                dependencies=dependencies or set(),
                tags=tags or set(),
                preferred_agent=preferred_agent,
                status=TaskStatus.PENDING,
            )

            # Update dependency graph
            if dependencies:
                self._update_dependency_graph(task_id, dependencies)

            # Check if task is ready or blocked
            if self._is_task_ready(metadata):
                metadata.status = TaskStatus.READY
            else:
                metadata.status = TaskStatus.BLOCKED
                logger.info(
                    f"Task {task_id} blocked, waiting for dependencies: "
                    f"{metadata.dependencies - self.completed_tasks}"
                )

            # Calculate dynamic priority
            dynamic_priority = self._calculate_dynamic_priority(metadata)

            # Create prioritized task (negative for max-heap)
            ptask = PrioritizedTask(
                priority=-dynamic_priority,  # Negative for max-heap
                task_id=task_id,
                metadata=metadata,
                payload=payload,
            )

            # Add to queue and index
            heapq.heappush(self.queue, ptask)
            self.tasks[task_id] = ptask

            logger.info(
                f"Enqueued task '{task_id}' with priority {dynamic_priority:.1f} "
                f"(base={base_priority}, status={metadata.status.value})"
            )

            return True

    def dequeue(self, skip_blocked: bool = True) -> Optional[tuple[str, Any, TaskMetadata]]:
        """
        Get highest priority task from queue.

        Args:
            skip_blocked: Whether to skip tasks waiting on dependencies

        Returns:
            (task_id, payload, metadata) or None if queue empty
        """
        with self.lock:
            while self.queue:
                # Recalculate priorities for aging
                if self.enable_aging:
                    self._recompute_priorities()

                # Get highest priority task
                ptask = heapq.heappop(self.queue)

                # Remove from index
                if ptask.task_id in self.tasks:
                    del self.tasks[ptask.task_id]

                # Check if ready
                if self._is_task_ready(ptask.metadata):
                    ptask.metadata.status = TaskStatus.RUNNING
                    self.running_tasks.add(ptask.task_id)

                    logger.info(
                        f"Dequeued task '{ptask.task_id}' with priority "
                        f"{-ptask.priority:.1f}"
                    )

                    return ptask.task_id, ptask.payload, ptask.metadata

                elif skip_blocked:
                    # Still blocked, put back for later
                    ptask.metadata.status = TaskStatus.BLOCKED
                    heapq.heappush(self.queue, ptask)
                    self.tasks[ptask.task_id] = ptask
                    continue
                else:
                    # Return blocked task anyway
                    return ptask.task_id, ptask.payload, ptask.metadata

            return None

    def mark_completed(self, task_id: str, success: bool = True):
        """Mark a task as completed and unblock dependents"""
        with self.lock:
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)

            self.completed_tasks.add(task_id)

            # Record for learning
            if task_id in self.tasks:
                metadata = self.tasks[task_id].metadata
                for tag in metadata.tags:
                    if tag not in self.execution_history:
                        self.execution_history[tag] = []
                    self.execution_history[tag].append({
                        "task_id": task_id,
                        "success": success,
                        "timestamp": time.time(),
                    })

            # Check if any blocked tasks can now run
            newly_ready = []
            for ptask in self.queue:
                if ptask.metadata.status == TaskStatus.BLOCKED:
                    if self._is_task_ready(ptask.metadata):
                        ptask.metadata.status = TaskStatus.READY
                        newly_ready.append(ptask.task_id)

            if newly_ready:
                logger.info(f"Tasks now ready after {task_id} completed: {newly_ready}")

            # Trigger priority recomputation
            if self.queue:
                self._recompute_priorities()

            self._save_history()

    def mark_failed(self, task_id: str, retry: bool = True):
        """Mark a task as failed and optionally re-queue for retry"""
        with self.lock:
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)

            # Record failure for learning
            self.mark_completed(task_id, success=False)

            # Check if should retry
            if retry and task_id in self.tasks:
                metadata = self.tasks[task_id].metadata
                if metadata.retry_count < metadata.max_retries:
                    metadata.retry_count += 1
                    metadata.status = TaskStatus.PENDING
                    logger.info(
                        f"Re-queuing failed task {task_id} "
                        f"(attempt {metadata.retry_count + 1}/{metadata.max_retries})"
                    )
                    # Re-add to queue with updated priority
                    # (retry penalty will be applied automatically)
                    return
                else:
                    logger.error(
                        f"Task {task_id} exhausted retries "
                        f"({metadata.max_retries} attempts)"
                    )

    def _recompute_priorities(self):
        """Recompute all task priorities (for aging, deadline updates)"""
        if not self.queue:
            return

        # Rebuild heap with new priorities
        updated_tasks = []
        for ptask in self.queue:
            new_priority = self._calculate_dynamic_priority(ptask.metadata)
            updated_task = PrioritizedTask(
                priority=-new_priority,
                task_id=ptask.task_id,
                metadata=ptask.metadata,
                payload=ptask.payload,
            )
            updated_tasks.append(updated_task)

        self.queue = updated_tasks
        heapq.heapify(self.queue)

    def size(self) -> int:
        """Get number of tasks in queue"""
        with self.lock:
            return len(self.queue)

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        with self.lock:
            return len(self.queue) == 0

    def get_status(self) -> dict[str, Any]:
        """Get queue statistics"""
        with self.lock:
            blocked = sum(1 for t in self.queue if t.metadata.status == TaskStatus.BLOCKED)
            ready = sum(1 for t in self.queue if t.metadata.status == TaskStatus.READY)

            return {
                "total_queued": len(self.queue),
                "ready": ready,
                "blocked": blocked,
                "running": len(self.running_tasks),
                "completed": len(self.completed_tasks),
            }

    def _save_history(self):
        """Persist execution history for learning"""
        if not self.enable_learning:
            return

        history_file = self.cache_dir / "execution_history.json"
        try:
            # Keep only recent history (last 1000 entries per tag)
            trimmed_history = {
                tag: history[-1000:] for tag, history in self.execution_history.items()
            }
            with history_file.open("w") as f:
                json.dump(trimmed_history, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save execution history: {e}")

    def _load_history(self):
        """Load execution history from disk"""
        if not self.enable_learning:
            return

        history_file = self.cache_dir / "execution_history.json"
        if history_file.exists():
            try:
                with history_file.open("r") as f:
                    self.execution_history = json.load(f)
                logger.info(f"Loaded execution history for {len(self.execution_history)} tags")
            except Exception as e:
                logger.warning(f"Failed to load execution history: {e}")
