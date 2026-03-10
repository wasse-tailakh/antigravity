import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.logger import LoggerSetup, get_logger
from orchestrator.executor import Executor

# Setup logging
LoggerSetup.setup(name="demo_review", level=10)  # DEBUG
logger = get_logger(__name__)

def main():
    print("\n" + "="*70)
    print("  PHASE 3A DEMO: Review Loop and Retry Policy")
    print("="*70 + "\n")
    
    executor = Executor()
    
    # We ask the agent to do something intentionally difficult or prone to failure/correction
    # so we can observe the Reviewer giving feedback and the Executor retrying.
    task = """
    Please create a file called 'math_test.txt' and inside it write ONLY 
    the result of 9999 multiplied by 123456 as a single number.
    DO NOT explain. DO NOT write words. JUST the number.
    """
    
    print(f"Task: {task}")
    print("\nExecuting...\n")
    
    results = executor.execute_task(task)
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    for result in results:
        print(f"Step {result.get('step_id', '?')}:")
        print(f"  Description: {result.get('description')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Attempts: {result.get('attempts')}")
        print(f"  Output: {result.get('output')}")
        if result.get('error'):
            print(f"  Error: {result.get('error')}")
        print("-" * 50)
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
