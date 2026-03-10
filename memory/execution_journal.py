from orchestrator.execution_state import StepResult
from memory.memory_store import SQLiteMemoryStore
from memory.memory_policy import MemoryPolicy

class ExecutionJournal:
    """
    Maintains a structured ledger of step results during an active task, 
    persisting them to the Memory Store for auditing and eventual summarization.
    """
    def __init__(self, task_id: str, store: SQLiteMemoryStore, policy: MemoryPolicy):
        self.task_id = task_id
        self.store = store
        self.policy = policy
        self.entries = []
        
    def record_step(self, step_info: dict, result: StepResult):
        action = step_info.get("action", "unknown")
        output_to_save = self.policy.truncate_for_journal(result.output or result.error or "")
        
        self.store.append_journal_entry(
            task_id=self.task_id,
            step_id=result.step_id,
            action=action,
            provider=result.provider_used,
            status=result.status,
            output=output_to_save
        )
        
        self.entries.append({
            "step_id": result.step_id,
            "action": action,
            "status": result.status,
            "output": output_to_save
        })
        
    def get_full_journal_text(self) -> str:
        """Returns a formatted string of the entire execution for the Summarizer."""
        if not self.entries:
            return "No steps executed."
            
        lines = []
        for e in self.entries:
            lines.append(f"Step {e['step_id']} ({e['action']}) - {e['status'].upper()}: {e['output']}")
        return "\n".join(lines)
