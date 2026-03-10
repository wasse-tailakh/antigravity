import argparse

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Antigravity: Cost-optimized multi-agent orchestration for practical AI workflows."
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # --- RUN Command ---
    run_parser = subparsers.add_parser("run", help="Execute a specific workflow")
    run_parser.add_argument("workflow", choices=["project-update", "research", "debug", "devops", "continuation"], help="Name of the workflow to run")
    
    # Workflow specific arguments
    # Ideally these would be specialized subparsers per workflow, but we'll use generic args for simplicity
    run_parser.add_argument("--target", type=str, help="Target file/module for the workflow (e.g., project-update, debug)")
    run_parser.add_argument("--goal", type=str, help="Goal or topic for the workflow (e.g., project-update, devops, research)")
    run_parser.add_argument("--error", type=str, help="Error traceback or message (for debug workflow)")
    run_parser.add_argument("--task-id", type=str, help="Previous task ID to load memory from (for continuation workflow)")
    
    # --- WORKFLOWS Command ---
    workflows_parser = subparsers.add_parser("workflows", help="Manage workflows")
    workflows_subparsers = workflows_parser.add_subparsers(dest="subcommand", required=True)
    workflows_subparsers.add_parser("list", help="List all available workflows")
    
    # --- MEMORY Command ---
    memory_parser = subparsers.add_parser("memory", help="Inspect orchestrator memory")
    memory_subparsers = memory_parser.add_subparsers(dest="subcommand", required=True)
    memory_show = memory_subparsers.add_parser("show", help="Show short term or task memory")
    memory_show.add_argument("--task-id", type=str, default="latest", help="Task ID to show memory for")
    
    # --- RUNS Command ---
    runs_parser = subparsers.add_parser("runs", help="Inspect past runs")
    runs_subparsers = runs_parser.add_subparsers(dest="subcommand", required=True)
    runs_subparsers.add_parser("list", help="List recent runs")
    
    # --- DOCTOR Command ---
    subparsers.add_parser("doctor", help="Check system dependencies, API keys, and database health")
    
    return parser
