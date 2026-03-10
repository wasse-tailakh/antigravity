from __future__ import annotations

DEFAULT_PROVIDER = "gemini"
ESCALATION_PROVIDER = "claude"

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-latest"


def choose_provider(
    task_type: str = "general",
    complexity_score: int = 0,
    allow_escalation: bool = True,
) -> str:
    """
    Cheap-by-default provider policy.
    """
    task_type = (task_type or "").lower()

    if allow_escalation and (
        complexity_score >= 8 or task_type in {"architecture", "debugging", "complex_code"}
    ):
        return ESCALATION_PROVIDER

    return DEFAULT_PROVIDER
