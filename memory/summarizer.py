import os
from pathlib import Path

from agents.gemini_agent import GeminiAgent
from memory.execution_journal import ExecutionJournal
from memory.memory_store import SQLiteMemoryStore
from memory.memory_policy import MemoryPolicy
from config.logger import get_logger

logger = get_logger("Summarizer")

class Summarizer:
    """
    Takes an entire ExecutionJournal and compresses it 
    into a brief summary using an LLM.
    """
    def __init__(self, prompt_path: str = None):
        self.agent = GeminiAgent()
        
        
        if prompt_path is None:
            project_root = Path(__file__).resolve().parent.parent
            self.prompt_path = project_root / "prompts" / "summarizer.txt"
        else:
            self.prompt_path = Path(prompt_path)
            
        self.system_prompt = self._load_prompt()
        
    def _load_prompt(self) -> str:
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Summarizer prompt not found at {self.prompt_path}. Using fallback.")
            return "Summarize the following task execution journal into a concise 2-3 sentence paragraph focusing on what was changed or achieved."
            
    def summarize_journal(self, user_prompt: str, journal_text: str) -> str:
        """Calls the LLM to compress the entire journal text."""
        llm_prompt = f"{self.system_prompt}\n\nORIGINAL USER REQUEST:\n{user_prompt}\n\nEXECUTION JOURNAL:\n{journal_text}\n\nProvide the summary below:"
        
        try:
            # Not using backoff here purposefully to keep memory generation fast and non-critical.
            # If summarization fails, we just return a default summary.
            summary = self.agent.run(llm_prompt, context={})
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to summarize journal: {e}")
            return "Failed to summarize task execution."
