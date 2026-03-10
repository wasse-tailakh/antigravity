import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.executor import Executor
from config.logger import get_logger

logger = get_logger("Workflow:ResearchSummary")

def run_research_workflow(topic: str, target_dir: str = "."):
    """
    Workflow 2: Research & Summarization Agent
    Scans a directory for files related to a topic, reads them, distills the 
    knowledge, and returns the summarized findings, automatically persisting 
    them to Long-Term Task Memory via the Executor.
    """
    logger.info(f"Starting Research Workflow: Topic='{topic}', Dir='{target_dir}'")
    
    executor = Executor()
    
    orchestration_prompt = f"""
    You are performing a Research and Summarization workflow.
    Topic: "{topic}"
    Target Directory: {target_dir}
    
    Please execute the following sequence:
    1. Scan the target directory (non-destructively) to find files related to the Topic.
    2. Read the contents of the relevant files.
    3. Synthesize the findings into a coherent summary.
    4. Write the final summary to a new file called 'research_report_{topic.replace(' ', '_')}.md'.
    """
    
    results = executor.execute_task(orchestration_prompt)
    
    logger.info("\n--- Workflow Execution Results ---")
    for r in results:
        logger.info(f"Step {r.get('step_id')} [{r.get('provider_used')}]: {r.get('status')} (Attempts: {r.get('attempts')})")
        
    return results

if __name__ == "__main__":
    print("Research & Summarization Workflow")
    print("---------------------------------")
    
    # We will research the memory stack we just built in Phase 5A
    os.makedirs("dummy_docs", exist_ok=True)
    with open("dummy_docs/memory_arch.txt", "w") as f:
         f.write("We use SQLite for Task Memory and an Execution Journal. Short term memory is isolated via a rolling queue.")
    
    topic = "Memory Architecture Details"
    dir_to_scan = "dummy_docs"
    
    run_research_workflow(topic, dir_to_scan)
    
    report_name = f"research_report_{topic.replace(' ', '_')}.md"
    if os.path.exists(report_name):
        print(f"\n--- Final Report ({report_name}) ---")
        with open(report_name, "r") as f:
            print(f.read())
            
        # Cleanup
        os.remove(report_name)
    else:
        print("\nFailed to generate report.")
