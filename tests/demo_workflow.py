import os
import sys

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from config.logger import get_logger

logger = get_logger("DemoWorkflow")

def main():
    logger.info("Starting Phase 2A Demo Workflow...")
    executor = Executor()
    
    # We ask the system to perform a workflow that requires all 3 skills:
    # 1. Read README.md (File Skill)
    # 2. Extract info and write to notes.txt (File Skill)
    # 3. Check git status to see the new file (Git Skill/Shell Skill)
    
    task_prompt = "Read README.md, create a file called notes.txt with a very short 1-sentence project summary, then run 'git status' or use the git tool to check the status."
    
    logger.info(f"Submitting task: {task_prompt}")
    
    results = executor.execute_task(task_prompt)
    
    logger.info("Demo Workflow execution complete. Check the logs above to see the tool interactions!")

if __name__ == "__main__":
    main()
