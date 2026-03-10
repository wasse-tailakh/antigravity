import os
import sqlite3
from cli.formatters import print_workflow_result, print_error, print_banner
from workflows.project_update import run_project_update_workflow
from workflows.research_summary import run_research_workflow
from workflows.debugging import run_debugging_workflow
from workflows.devops import run_devops_workflow
from workflows.continuation import run_continuation_workflow

def handle_run(args):
    workflow = args.workflow
    results = None
    
    if workflow == "project-update":
        if not args.target or not args.goal:
            print_error("Workflow 'project-update' requires --target and --goal")
        results = run_project_update_workflow(args.target, args.goal)
        
    elif workflow == "research":
        if not args.goal:
            print_error("Workflow 'research' requires --goal (topic)")
        target_dir = args.target or "."
        results = run_research_workflow(args.goal, target_dir)
        
    elif workflow == "debug":
        if not args.target or not args.error:
            print_error("Workflow 'debug' requires --target and --error")
        results = run_debugging_workflow(args.error, args.target)
        
    elif workflow == "devops":
        if not args.goal:
            print_error("Workflow 'devops' requires --goal")
        results = run_devops_workflow(args.goal)
        
    elif workflow == "continuation":
        if not args.task_id or not args.goal:
            print_error("Workflow 'continuation' requires --task-id (previous task description/id) and --goal (new task)")
        results = run_continuation_workflow(args.task_id, args.goal)
        
    print_workflow_result(workflow, results)


def handle_workflows(args):
    if args.subcommand == "list":
        print("\nAvailable Workflows:")
        print("  project-update  : Analyzes a target file and applies a requested refactor.")
        print("  research        : Scans a target directory, summarizes content based on a goal/topic.")
        print("  debug           : Reads an error traceback and patches the target file.")
        print("  devops          : Safely executes system shell commands to achieve a goal.")
        print("  continuation    : Chains tasks, relying on SQLite memory context from a previous run.\n")

def handle_memory(args):
    if args.subcommand == "show":
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        
        print("\n--- Task Memory (SQLite) ---")
        summaries = store.get_recent_task_summaries(limit=5)
        if not summaries:
            print("No task memories found.")
        for task in summaries:
            print(f"[{task.get('timestamp')}] Task: {task.get('user_prompt')[:50]}...")
            print(f"Summary: {task.get('summary')}\n")

def handle_runs(args):
    if args.subcommand == "list":
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        
        print("\n--- Recent Execution Journals ---")
        try:
            with sqlite3.connect(store.db_path) as conn:
                cursor = conn.cursor()
                # Use subquery to get distinct runs from journal based on task_id or just list recent tasks
                cursor.execute(
                    "SELECT task_id, timestamp FROM task_memory ORDER BY timestamp DESC LIMIT 5"
                )
                runs = cursor.fetchall()
                if not runs:
                    print("No runs found.")
                for r in runs:
                    print(f"Run ID: {r[0]} at {r[1]}")
        except Exception as e:
            # Fallback if sqlite3 is not explicitly imported in commands, we can just use store logic
            try:
                summaries = store.get_recent_task_summaries(limit=5)
                if not summaries:
                    print("No runs found.")
                for s in summaries:
                    print(f"Run ID: {s.get('task_id')} at {s.get('timestamp')}")
            except Exception as e2:
                print(f"Failed to list runs: {e2}")

def handle_doctor(args):
    print("\n--- Antigravity Doctor ---")
    keys = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    for k in keys:
        flag = "[OK]" if os.environ.get(k) else "[FAIL] (Missing)"
        print(f"{k}: {flag}")
        
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        print("SQLite memory_store: [OK] (Writable)")
    except Exception as e:
        print(f"SQLite memory_store: [FAIL] ({e})")
        
    print("Doctor check complete.\n")
