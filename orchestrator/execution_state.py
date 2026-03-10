from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


StepStatus = Literal["pending", "running", "success", "failed", "retrying", "skipped"]


@dataclass
class StepResult:
    step_id: str
    status: StepStatus
    output: Any = None
    error: str | None = None
    tool_used: str | None = None
    provider_used: str | None = None
    attempts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionState:
    task_id: str
    user_prompt: str
    current_step_index: int = 0
    steps: list[dict[str, Any]] = field(default_factory=list)
    results: list[StepResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_result(self, result: StepResult) -> None:
        self.results.append(result)

    def current_step(self) -> dict[str, Any] | None:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self) -> None:
        self.current_step_index += 1

    def last_result(self) -> StepResult | None:
        return self.results[-1] if self.results else None

    def is_complete(self) -> bool:
        return self.current_step_index >= len(self.steps)
