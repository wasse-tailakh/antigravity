import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from orchestrator.executor import Executor

def main():
    print("=== Demo: Smart Retries and Escalation ===\n")
    print("In this demo, we will ask the agent to run a shell command that intentionally fails (`exit 1`).")
    print("1. The Reviewer will flag the non-zero exit code as an error.")
    print("2. The RetryPolicy will classify it as UNKNOWN/RETRYABLE.")
    print("3. The system will retry it several times, eventually escalating to 'claude' before failing.\n")
    
    exe = Executor()
    
    task_desc = "Please use the shell skill to run the exact command: `exit 1`. Do not run anything else."
    
    print(f"Task: {task_desc}\n")
    results = exe.execute_task(task_desc)
    
    print("\n--- Final Results ---")
    for r in results:
        print(f"\nStep ID: {r.get('step_id')}")
        print(f"Status: {r.get('status')}")
        print(f"Provider Used: {r.get('provider_used')}")
        print(f"Attempts: {r.get('attempts')}")
        print(f"Error: {r.get('error')}")
        print(f"Failure Category: {r.get('metadata', {}).get('failure_category', 'None')}")
        
    print("\nNote the number of attempts and that it escalated to claude (if gemini failed repeatedly) before halting.")
    print("=== Demo Complete ===")

if __name__ == "__main__":
    main()

