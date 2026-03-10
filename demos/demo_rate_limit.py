import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Make sure we can import from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from orchestrator.executor import Executor
from memory.response_cache import response_cache

def run_task(executor, task_desc, thread_id):
    print(f"\n[Thread {thread_id}] Starting task: '{task_desc}'")
    start = time.time()
    results = executor.execute_task(task_desc)
    duration = time.time() - start
    print(f"\n[Thread {thread_id}] Finished in {duration:.2f}s with {len(results)} steps.")
    return results

def main():
    print("=== Demo: Rate Limiting, Backoff, and Response Coalescing ===\n")
    
    # 1. Clear caches
    print("Clearing caches to start fresh...")
    response_cache.clear()
    
    # Initialize Executor
    exe = Executor()
    
    # Task to run concurrently
    task = "List the files in the current directory and explain what this project is about briefly."
    
    # 2. Run 3 identical tasks concurrently
    print(f"\n--- Scenario: 3 Concurrent Identical Tasks ---")
    print("Expected behavior: Only ONE thread computes the plan and route. The other two will COALESCE (wait) and reuse the cache immediately, saving LLM calls.\n")
    
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = []
        for i in range(3):
            futures.append(pool.submit(run_task, exe, task, i+1))
            
        for f in futures:
            f.result()
            
    print("\n--- Scenario Complete ---\n")
    
    # 3. Check for 429 Backoff handling
    print("\n--- Scenario: Overloading the API (Testing Rate Limits & Backoff) ---")
    print("We will attempt to send many rapid distinct requests to trigger 429s.")
    print("Expected behavior: The RateLimitPolicy or BackoffLogic should catch 429s, print a warning, sleep, and gracefully retry without crashing.\n")
    
    rapid_tasks = [
        "What is 1+1?",
        "What is 2+2?",
        "What is 3+3?",
        "What is 4+4?",
        "What is 5+5?",
        "What is 6+6?",
        "What is 7+7?",
        "What is 8+8?",
        "What is 9+9?",
        "What is 10+10?"
    ]
    
    # Run them rapidly in sequence.
    for i, t in enumerate(rapid_tasks):
        print(f"\n[Rapid Task {i+1}] {t}")
        exe.execute_task(t)
        
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    main()
