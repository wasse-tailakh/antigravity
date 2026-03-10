import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from orchestrator.retry_policy import FailureCategory, RetryDecision
from orchestrator.execution_state import StepResult


@patch("orchestrator.executor.BackoffLogic.execute_with_backoff")
def test_executor_retries_and_escalates(mock_backoff):
    """
    Test that the executor correctly retries a step that initially fails,
    and handles escalation properly.
    """
    exe = Executor()
    
    # Mock planner to return 1 step
    mock_plan = [{"id": 1, "description": "Generate some complex code", "agent_type": "gemini"}]
    
    # Mock reviewer to fail twice, then succeed
    exe.reviewer.review_step = MagicMock(side_effect=[
        (False, "Failed review 1: Syntax error"),
        (False, "Failed review 2: Still syntax error"),
        (True, "Successfully fixed syntax error")
    ])
    
    with patch.object(exe.planner, 'create_plan', return_value=mock_plan):
        mock_backoff.return_value = "{\"action\": \"write_file\", \"filepath\": \"foo.py\", \"content\": \"print(x)\"}"
        
        results = exe.execute_task("Do the thing")
        
        assert len(results) == 1
        result = results[0]
        
        assert result['status'] == "success", "The 3rd attempt should have succeeded."
        assert result['attempts'] == 3, "It should have taken 3 attempts."
        
        # Check that it escalated to claude!
        # Initial: gemini -> attempt 1 fails -> retry decision says shouldn't escalate yet (attempt 1/3)
        # Attempt 2: gemini -> fails -> retry decision dictates escalation (attempt 2/3)
        # Attempt 3: claude -> succeeds
        assert result['provider_used'] == "claude", "Should have escalated to Claude"

@patch("orchestrator.executor.BackoffLogic.execute_with_backoff")
def test_executor_halts_on_policy_violation(mock_backoff):
    """
    Test that the executor halts entirely (no retries) if a policy violation occurs.
    """
    exe = Executor()
    
    # Trigger a policy violation explicitly by overriding the mock output
    mock_plan = [{"id": 1, "description": "Delete root directory", "agent_type": "gemini"}]
    
    exe.reviewer.review_step = MagicMock(return_value=(False, "Security violation: Access denied"))
    
    with patch.object(exe.planner, 'create_plan', return_value=mock_plan):
        mock_backoff.return_value = "{\"action\": \"shell\", \"command\": \"rm -rf /\"}"
        
        results = exe.execute_task("Do the thing")
        
        assert len(results) == 1
        result = results[0]
        
        assert result['status'] == "failed"
        assert result['attempts'] == 1, "Should not retry a policy violation"
        assert result['metadata'].get("failure_category") == "POLICY_VIOLATION"
