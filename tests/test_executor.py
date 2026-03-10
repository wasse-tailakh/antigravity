import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from orchestrator.execution_state import StepResult

def test_executor_initialization():
    """Verify that the Executor initializes with its core components."""
    exe = Executor()
    assert exe.planner is not None
    assert exe.router is not None
    assert exe.cost_guard is not None
    assert exe.tool_registry is not None
    assert exe.rate_limit_policy is not None

def test_executor_fast_fail_on_plan_error():
    """If the planner completely fails to return a plan, we return empty."""
    exe = Executor()
    
    # Mock the planner to throw an exception
    with patch.object(exe.planner, 'create_plan', side_effect=Exception("API Down")):
        results = exe.execute_task("Do something")
        assert results == []

@patch("orchestrator.executor.BackoffLogic.execute_with_backoff")
def test_executor_step_execution(mock_backoff):
    """Verify an executor can process a basic plan from end-to-end if mocked."""
    exe = Executor()
    
    # Setup mock plan
    mock_plan = [{"id": 1, "description": "Say Hello", "agent_type": "gemini"}]
    with patch.object(exe.planner, 'create_plan', return_value=mock_plan):
        
        # When backoff tries to run _llm_call, pretend the LLM returned "Hello"
        mock_backoff.return_value = "Hello World"
        
        results = exe.execute_task("Test task")
        
        assert len(results) == 1
        assert results[0]['status'] == "success"
        assert results[0]['output'] == "Hello World"
        assert results[0]['provider_used'] == "gemini"
