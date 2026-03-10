from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskCostState:
    task_id: str
    llm_calls: int = 0
    tool_calls: int = 0
    input_chars: int = 0
    output_chars: int = 0
    provider_calls: dict[str, int] = field(default_factory=dict)
    escalated_to_claude: bool = False

    def record_llm_call(
        self,
        provider: str,
        input_text: str = "",
        output_text: str = "",
    ) -> None:
        self.llm_calls += 1
        self.input_chars += len(input_text or "")
        self.output_chars += len(output_text or "")
        self.provider_calls[provider] = self.provider_calls.get(provider, 0) + 1

    def record_tool_call(self) -> None:
        self.tool_calls += 1


class CostGuard:
    """
    Guardrail for limiting token-heavy workflows.

    Philosophy:
    - Gemini is cheap/default.
    - Claude is expensive/escalation only.
    - Deterministic tool actions should not consume LLM calls.
    """

    def __init__(
        self,
        max_llm_calls_per_task: int = 4,
        max_tool_calls_per_task: int = 12,
        max_input_chars_per_task: int = 20000,
        max_output_chars_per_task: int = 12000,
        max_claude_calls_per_task: int = 1,
    ) -> None:
        self.max_llm_calls_per_task = max_llm_calls_per_task
        self.max_tool_calls_per_task = max_tool_calls_per_task
        self.max_input_chars_per_task = max_input_chars_per_task
        self.max_output_chars_per_task = max_output_chars_per_task
        self.max_claude_calls_per_task = max_claude_calls_per_task

    def can_call_llm(self, state: TaskCostState, provider: str) -> tuple[bool, str | None]:
        if state.llm_calls >= self.max_llm_calls_per_task:
            return False, "Max LLM calls reached for this task."

        if state.input_chars >= self.max_input_chars_per_task:
            return False, "Max input chars reached for this task."

        if state.output_chars >= self.max_output_chars_per_task:
            return False, "Max output chars reached for this task."

        if provider == "claude":
            claude_calls = state.provider_calls.get("claude", 0)
            if claude_calls >= self.max_claude_calls_per_task:
                return False, "Claude escalation budget exhausted."

        return True, None

    def can_call_tool(self, state: TaskCostState) -> tuple[bool, str | None]:
        if state.tool_calls >= self.max_tool_calls_per_task:
            return False, "Max tool calls reached for this task."
        return True, None

    def should_escalate_to_claude(
        self,
        state: TaskCostState,
        reason: str,
        complexity_score: int = 0,
    ) -> bool:
        """
        Escalate only for genuinely hard reasoning/code tasks.
        """
        if state.escalated_to_claude:
            return False

        if complexity_score >= 8:
            return True

        hard_keywords = {
            "architecture",
            "refactor",
            "debug",
            "complex",
            "multi-file",
            "design",
            "fix bug",
        }
        lowered = reason.lower()
        return any(k in lowered for k in hard_keywords)

    def mark_claude_escalation(self, state: TaskCostState) -> None:
        state.escalated_to_claude = True

    def summarize_budget(self, state: TaskCostState) -> dict[str, Any]:
        return {
            "task_id": state.task_id,
            "llm_calls": state.llm_calls,
            "tool_calls": state.tool_calls,
            "input_chars": state.input_chars,
            "output_chars": state.output_chars,
            "provider_calls": state.provider_calls,
            "escalated_to_claude": state.escalated_to_claude,
        }
