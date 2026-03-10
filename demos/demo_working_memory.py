import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from orchestrator.executor import Executor

def main():
    print("=== Demo: Working Memory & Task Memory ===\n")
    print("We will execute two tasks to demonstrate how memory persists across executions.")
    
    exe = Executor()
    
    # Task 1: Do an action to generate facts
    task1_desc = "Write a file named 'memory_test.txt' in the project root containing the sentence: 'The secret password for the database is ORION-99'."
    print(f"--- TASK 1 ---\n{task1_desc}\n")
    
    exe.execute_task(task1_desc)
    
    print("\n\nTask 1 completed. The Executor should have summarized this action and saved it to TaskMemory.")
    print("Now we will execute Task 2, which requires knowledge of Task 1.")
    
    # Task 2: Ask a question relying on recent task memory
    task2_desc = "Without reading any files, please tell me the secret database password based on what you remember we just did in the previous task."
    print(f"\n--- TASK 2 ---\n{task2_desc}\n")
    
    results = exe.execute_task(task2_desc)
    
    print("\n--- Final Results for Task 2 ---")
    for r in results:
        print(f"\nStep ID: {r.get('step_id')}")
        print(f"Status: {r.get('status')}")
        print(f"Output: {r.get('output')}")
        
    print("\nNotice how the LLM was able to answer the question using the injected memory context without invoking the file reader tool.")
    
    # Cleanup
    try:
        os.remove(os.path.join(os.path.abspath(os.path.dirname(__file__)), "memory_test.txt"))
        print("\nCleaned up 'memory_test.txt'.")
    except OSError:
        pass

    print("=== Demo Complete ===")

if __name__ == "__main__":
    main()
