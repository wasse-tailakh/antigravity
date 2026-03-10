import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from config.logger import get_logger

logger = get_logger("Workflow:Debugging")

def run_debugging_workflow(error_traceback: str, target_file: str):
    """
    Workflow 3: Debugging Assistant
    Accepts a traceback, reads the suspect code, proposes a patch, applies it, 
    and returns the execution success state.
    """
    logger.info(f"Starting Debugging Workflow for {target_file}")
    
    executor = Executor()
    
    orchestration_prompt = f"""
    You are performing a Debugging workflow.
    Target File: {target_file}
    
    The user reported the following Error Traceback:
    ```
    {error_traceback}
    ```
    
    Please execute the following sequence:
    1. Read the Target File to locate the line causing the error.
    2. Write a patch to fix the bug.
    3. Use the FileSkill to apply the patch to the Target File.
    4. If the fix requires importing a new module, ensure the import is added.
    """
    
    results = executor.execute_task(orchestration_prompt)
    
    logger.info("\n--- Workflow Execution Results ---")
    for r in results:
        logger.info(f"Step {r.get('step_id')} [{r.get('provider_used')}]: {r.get('status')} (Attempts: {r.get('attempts')})")
        
    return results

if __name__ == "__main__":
    print("Debugging Workflow")
    print("------------------")
    
    test_filepath = "dummy_buggy_code.py"
    with open(test_filepath, "w") as f:
        f.write("def divide_numbers(a, b):\n    return a / b\n\nprint(divide_numbers(10, 0))\n")
        
    print(f"Created buggy file {test_filepath}.")
    
    traceback = "ZeroDivisionError: division by zero at line 2 in divide_numbers"
    
    run_debugging_workflow(traceback, test_filepath)
    
    print("\n--- Final File Content (Should handle ZeroDivisionError) ---")
    with open(test_filepath, "r") as f:
        print(f.read())
        
    os.remove(test_filepath)
