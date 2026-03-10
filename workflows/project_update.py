import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from config.logger import get_logger

logger = get_logger("Workflow:ProjectUpdate")

def run_project_update_workflow(target_filepath: str, refactor_goal: str):
    """
    Workflow 1: Project Update Agent
    Reads a target file, analyzes it, proposes a refactor based on the goal,
    applies the change, reviews syntax, and summarizes the work in Task Memory.
    """
    logger.info(f"Starting Project Update Workflow for {target_filepath}")
    
    executor = Executor()
    
    orchestration_prompt = f"""
    You are to perform a project update workflow.
    Target File: {target_filepath}
    Goal: {refactor_goal}
    
    Please execute the following sequence:
    1. Read the target file to understand its current state.
    2. Develop a plan to refactor the file to meet the Goal.
    3. Modify the file using the appropriate tools.
    4. Run a syntax check or basic test if possible to review the change.
    
    If the changes fail, rely on your retry policy and error feedback to correct the issue.
    """
    
    results = executor.execute_task(orchestration_prompt)
    
    logger.info("\n--- Workflow Execution Results ---")
    for r in results:
        logger.info(f"Step {r.get('step_id')} [{r.get('provider_used')}]: {r.get('status')} (Attempts: {r.get('attempts')})")
        
    return results

if __name__ == "__main__":
    print("Project Update Workflow")
    print("-----------------------")
    # A safe dummy file to test the workflow
    test_filepath = "dummy_refactor_test.py"
    with open(test_filepath, "w") as f:
        f.write("def calculate_total(a, b):\n    # TODO: Add logging\n    return a + b\n")
        
    print(f"Created dummy file {test_filepath} for testing.")
    
    goal = "Refactor the function to use Python 3 type hints, add proper docstrings, and actually add the logging module to output the inputs before returning."
    
    run_project_update_workflow(test_filepath, goal)
    
    print("\n--- Final File Content ---")
    with open(test_filepath, "r") as f:
        print(f.read())
        
    # Optional cleanup
    # os.remove(test_filepath)
