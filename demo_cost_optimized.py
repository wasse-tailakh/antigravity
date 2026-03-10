import sys
import os
from orchestrator.executor import Executor
from config.logger import get_logger

# Add the project directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

logger = get_logger("DemoCostOptimized")

def run_optimization_demo():
    print("\n" + "="*70)
    print("  PHASE 3B DEMO: Cost-Optimized Multi-Agent Execution")
    print("="*70)
    
    # Task 1: A simple generic task that should run entirely on Gemini Flash
    # without touching Claude 3.5 Sonnet.
    task = """
    Please read the contents of 'README.md' and summarize what this project is about 
    in one short sentence. Write that sentence to a file called 'summary_test.txt'.
    """
    
    print(f"\nTask: {task}\n")
    print("Executing Task on initial run...\n")
    
    executor = Executor()
    
    # We will track how many tools and LLM calls were executed using our CostGuard
    print("--- RUN 1 (Cache MISS expected) ---")
    results_run_1 = executor.execute_task(task)
    
    llms_run_1 = executor.cost_guard._current_llm_calls
    tools_run_1 = executor.cost_guard._current_tool_calls
    
    print("\n\n--- RUN 2 (Cache HIT expected) ---")
    print("Executing the exact same task. Planner should hit the TaskCache.")
    
    # Run the exact same task again. 
    # The planner should pull from cache and skip the LLM planning phase.
    results_run_2 = executor.execute_task(task)
    
    llms_run_2 = executor.cost_guard._current_llm_calls
    tools_run_2 = executor.cost_guard._current_tool_calls

    print("\n" + "="*70)
    print("FINAL COST ANALYSIS")
    print("="*70)
    print(f"Run 1 LLM Calls: {llms_run_1}")
    print(f"Run 2 LLM Calls: {llms_run_2}")
    
    if llms_run_2 < llms_run_1:
         print("\nSUCCESS: TaskCache prevented redundant LLM calls on Run 2!")
    else:
         print("\nFAILED: TaskCache did not save LLM calls.")
         
    print("\nCheck the console logs to verify that Gemini (not Claude) handled the planning and routing.")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_optimization_demo()
