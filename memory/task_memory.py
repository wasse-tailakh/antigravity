from memory.memory_store import SQLiteMemoryStore
from memory.memory_policy import MemoryPolicy

class TaskMemory:
    """
    Handles persisting and retrieving finalized, high-level summaries 
    of completed tasks so that subsequent tasks can recall context.
    """
    def __init__(self, store: SQLiteMemoryStore, policy: MemoryPolicy):
        self.store = store
        self.policy = policy
        
    def save_task_summary(self, task_id: str, prompt: str, summary: str):
        """Persists the summarized knowledge of a completed task."""
        self.store.save_task_summary(task_id, prompt, summary)
        
    def get_recent_summaries_context(self) -> str:
        """
        Retrieves recent summaries to inject into the Planner and Router
        so they understand what the system just finished doing.
        """
        recent_tasks = self.store.get_recent_task_summaries(limit=self.policy.recent_tasks_context_limit)
        
        if not recent_tasks:
            return "No previous memory."
            
        lines = ["--- RECENT TASK HISTORY ---"]
        for t in reversed(recent_tasks): # Chronological order
            lines.append(f"Task: {t['user_prompt']}")
            lines.append(f"Summary: {t['summary']}")
            lines.append("----------------------------")
            
        return "\n".join(lines)
