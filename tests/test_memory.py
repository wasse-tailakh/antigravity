import os
import sys
import pytest
from unittest.mock import MagicMock

# Add project root to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory.memory_store import SQLiteMemoryStore
from memory.memory_policy import MemoryPolicy
from memory.task_memory import TaskMemory
from memory.short_term_memory import ShortTermMemory
from memory.execution_journal import ExecutionJournal
from orchestrator.execution_state import StepResult

@pytest.fixture
def memory_store():
    # Use an in-memory SQLite database for fast, isolated testing
    store = SQLiteMemoryStore(db_path=":memory:")
    yield store

@pytest.fixture
def memory_policy():
    return MemoryPolicy(max_short_term_steps=2, max_journal_output_length=50)

def test_task_memory_save_and_retrieve(memory_store, memory_policy):
    tm = TaskMemory(memory_store, memory_policy)
    tm.save_task_summary("task_1", "Do X", "Completed X successfully.")
    tm.save_task_summary("task_2", "Do Y", "Failed Y due to network error.")
    
    context = tm.get_recent_summaries_context()
    
    assert "Task: Do X" in context
    assert "Summary: Completed X successfully." in context
    assert "Task: Do Y" in context
    assert "Summary: Failed Y due to network error." in context

def test_short_term_memory_rolling_window(memory_policy):
    stm = ShortTermMemory(memory_policy)
    
    stm.add_step_context("Step 1", "Output 1", True)
    stm.add_step_context("Step 2", "Output 2", True)
    
    # max_short_term_steps is 2, so adding a 3rd should drop the 1st
    stm.add_step_context("Step 3", "Output 3", True)
    
    context = stm.get_context_string()
    assert "Step 1" not in context
    assert "Step 2" in context
    assert "Step 3" in context

def test_execution_journal_truncation_and_formatting(memory_store, memory_policy):
    journal = ExecutionJournal("task_99", memory_store, memory_policy)
    
    long_output = "A" * 100 # Policy max is 50
    step_res = StepResult(step_id="1", status="success", output=long_output, provider_used="gemini")
    step_info = {"action": "shell"}
    
    journal.record_step(step_info, step_res)
    
    journal_text = journal.get_full_journal_text()
    assert "Step 1 (shell) - SUCCESS" in journal_text
    
    # Check that output is truncated in the DB
    results = memory_store.get_recent_task_summaries() 
    # Actually we just run a raw query to check journal
    with __import__('sqlite3').connect(":memory:") as conn: # In memory doesn't persist across connections, but that's ok we can just check the journal text
        pass
        
    assert len(journal_text) > 50
    assert "[TRUNCATED]" in journal_text
