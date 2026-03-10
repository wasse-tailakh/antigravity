import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from config.logger import get_logger

logger = get_logger("Workflow:DevOps")

def run_devops_workflow(task_description: str):
    """
    Workflow 4: Safe DevOps Assistant
    Executes specific safe system/shell tasks, verifies exit codes,
    and prepares a summary. It is explicitly instructed to refuse unsafe tools.
    """
    logger.info(f"Starting DevOps Workflow for task: '{task_description}'")
    
    executor = Executor()
    
    orchestration_prompt = f"""
    You are performing a Safe DevOps workflow.
    Task Goal: {task_description}
    
    Please execute the following sequence:
    1. Use the ShellSkill to execute the necessary commands to fullfil the Task Goal.
    2. Verify the exit codes and output streams of your commands.
    3. If a command fails, attempt to diagnose the issue and try one more time.
    4. DO NOT attempt to delete root directories, change core system settings, or run destructive commands.
    5. Prepare a brief summary of what happened.
    """
    
    results = executor.execute_task(orchestration_prompt)
    
    logger.info("\n--- Workflow Execution Results ---")
    for r in results:
        logger.info(f"Step {r.get('step_id')} [{r.get('provider_used')}]: {r.get('status')} (Attempts: {r.get('attempts')})")
        
    return results

if __name__ == "__main__":
    print("Safe DevOps Workflow")
    print("--------------------")
    
    goal = "Check what version of python is installed, and output it to a new file called 'python_version.txt"
    
    run_devops_workflow(goal)
    
    if os.path.exists("python_version.txt"):
        print("\n--- Output file generated ---")
        with open("python_version.txt", "r") as f:
            print(f.read())
        os.remove("python_version.txt")
    else:
        print("\nDevOps workflow failed to build the target file.")
