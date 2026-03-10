from collections import deque
from memory.memory_policy import MemoryPolicy

class ShortTermMemory:
    """
    Manages the rolling context window of the currently active task.
    Prevents context bloat by dropping old intermediate steps based on policy.
    """
    def __init__(self, policy: MemoryPolicy):
        self.policy = policy
        # Use a deque to automatically drop older items when max length is reached
        self.recent_steps = deque(maxlen=self.policy.max_short_term_steps)
        
    def add_step_context(self, step_description: str, result_output: str, success: bool):
        """Adds a localized snapshot of a single executed step."""
        trunc_output = self.policy.truncate_for_journal(result_output)
        status = "SUCCESS" if success else "FAILED"
        context_str = f"[{status}] Step: {step_description}\nOutput: {trunc_output}"
        self.recent_steps.append(context_str)
        
    def get_context_string(self) -> str:
        """Returns the rolling context string to be injected into LLM prompts."""
        if not self.recent_steps:
            return "No previous steps executed in this task."
            
        return "\n\n---\n".join(self.recent_steps)
