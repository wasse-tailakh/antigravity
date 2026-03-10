from __future__ import annotations

from typing import Any

from orchestrator.execution_state import StepResult


class Reviewer:
    """
    Lightweight deterministic reviewer.
    Keep it cheap. Do not call LLM here unless absolutely necessary.
    """

    def review_step(
        self,
        step: dict[str, Any],
        result: StepResult,
    ) -> tuple[bool, str]:
        if result.status != "success":
            return False, result.error or "Step did not succeed."

        action = step.get("action", "").lower()

        if action in {"read_file", "write_file"}:
            if result.output is None and not result.metadata:
                return False, "File step returned no meaningful result."
            return True, "File step validated."

        if action in {"run_shell", "shell"}:
            if result.output is None:
                return False, "Shell step returned empty output."
            return True, "Shell step validated."

        if action in {"git_status", "git_commit", "git"}:
            return True, "Git step validated."

        # Generic fallback
        if result.error:
            return False, result.error

        return True, "Step validated."
