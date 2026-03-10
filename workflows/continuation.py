import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from config.logger import get_logger

logger = get_logger("Workflow:Continuation")

def run_continuation_workflow(task_1_desc: str, task_2_desc: str):
    """
    Workflow 5: Task Continuation
    Demonstrates chaining tasks across discrete Executor instances by relying
    entirely on the TaskMemory subsystem (SQLite DB) populated by Task 1 
    to provide the context necessary to complete Task 2.
    """
    logger.info("Starting Continuation Workflow")
    
    print("\n[Phase A] Running Task 1...")
    exe1 = Executor()
    exe1.execute_task(task_1_desc)
    
    print("\n[Phase B] Running Task 2 (Discrete Executor Instance)... ")
    exe2 = Executor()
    results = exe2.execute_task(task_2_desc)
    
    logger.info("\n--- Task 2 Execution Results ---")
    for r in results:
        logger.info(f"Step {r.get('step_id')} [{r.get('provider_used')}]: {r.get('status')} (Attempts: {r.get('attempts')})")
        
    return results

if __name__ == "__main__":
    print("Task Continuation Workflow")
    print("--------------------------")
    
    t1 = "Calculate 15 * 12 and write the answer inside a file named 'math_result.txt' in the project root."
    t2 = "Delete the 'math_result.txt' file you just created. You do not need to read it to know it exists, because you should remember creating it in the previous task."
    
    run_continuation_workflow(t1, t2)
    
    if os.path.exists("math_result.txt"):
        print("\nFailure! The file was not deleted, memory chaining may have failed.")
        os.remove("math_result.txt")
    else:
        print("\nSuccess! The file was deleted based on historical memory.")
