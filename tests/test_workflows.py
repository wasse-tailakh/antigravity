import pytest
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workflows.project_update import run_project_update_workflow
from workflows.research_summary import run_research_workflow
from workflows.debugging import run_debugging_workflow
from workflows.devops import run_devops_workflow
from workflows.continuation import run_continuation_workflow

# Note: Integration tests with actual LLMs can be flaky or cause heavy quota usage
# in CI. We should ideally mock the Executor, but for this specific test suite 
# demonstrating the real capability, we run them on tiny constrained problems.
# If rate limits are hit, these tests may fail.

@pytest.mark.skip(reason="Avoid hitting LLM quotas during standard rapid testing.")
def test_project_update_live():
    test_filepath = "test_target_update.py"
    with open(test_filepath, "w") as f:
        f.write("def add(a,b):\n  return a+b\n")
    
    results = run_project_update_workflow(test_filepath, "Add python 3 type hints to the function.")
    assert len(results) > 0
    assert results[-1].get('status') == 'success'
    
    with open(test_filepath, "r") as f:
        content = f.read()
    assert "int" in content or "float" in content
    
    os.remove(test_filepath)

@pytest.mark.skip(reason="Avoid hitting LLM quotas during standard rapid testing.")
def test_continuation_live():
    t1 = "Write the word 'ORANGE' inside a new file named 'color_test.txt' in the project root."
    t2 = "Delete the 'color_test.txt' file you created."
    
    run_continuation_workflow(t1, t2)
    assert not os.path.exists('color_test.txt')
