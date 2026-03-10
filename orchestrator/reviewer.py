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
            return False, result.error or "Step did not succeed. The tool or agent reported a failure."

        action = step.get("action", "").lower()

        # If it's a direct file action (less common now that we use tools directly, but kept for compatibility)
        if action in {"read_file", "write_file", "file"}:
            if result.output is None and not result.metadata:
                return False, "File operation failed: The step returned no meaningful result or output. Please verify paths and permissions."
            return True, "File step validated: Output received."

        if action in {"run_shell", "shell"}:
            if result.output is None:
                return False, "Shell command failed or produced no output. Please verify the command syntax."
            return True, "Shell step validated."

        if action in {"git_status", "git_commit", "git"}:
            if result.output is None:
                return False, "Git operation returned no output."
            return True, "Git step validated."

        # If the LLM just returned a generic text answer without specific action metadata
        if result.output and isinstance(result.output, str):
            if "error" in result.output.lower() and len(result.output) < 150:
                 return False, f"The output appears to contain an error message: {result.output}"
            if len(result.output.strip()) == 0:
                 return False, "The agent returned an empty markdown string."
                 
            return True, "Output appears valid."

        # Generic fallback
        if result.error:
            return False, f"Step execution resulted in an error: {result.error}"

        return True, "Step validated: Default criteria met."
