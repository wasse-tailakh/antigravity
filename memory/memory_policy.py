from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class MemoryPolicy:
    """
    Defines rules for what is kept, summarized, or discarded in memory.
    """
    # Max steps to keep in the short-term rolling window
    max_short_term_steps: int = 5 
    
    # Max length of characters to store for a single step's output in the journal
    max_journal_output_length: int = 2000 
    
    # Number of recent tasks to load into the planner/router context
    recent_tasks_context_limit: int = 3
    
    def truncate_for_journal(self, text: str) -> str:
        """Truncates exceedingly long outputs before saving them to the database."""
        if not text:
            return ""
        if len(text) > self.max_journal_output_length:
            return text[:self.max_journal_output_length] + "\n...[TRUNCATED]"
        return text
