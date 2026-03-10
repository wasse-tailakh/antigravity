from fastapi import APIRouter
import sqlite3
from typing import List
from api.schemas import APIResponse, APIError, RunStatusResponse, RunJournalSchema
from api.services import get_run_store

router = APIRouter()

@router.get("/", summary="List recent runs", description="Returns recent workflow runs from memory and the in-memory run store.")
def list_runs(limit: int = 10):
    results = []
    
    # First, include in-memory background runs
    run_store = get_run_store()
    for task_id, run_status in run_store.items():
        results.append({"task_id": task_id, "workflow": run_status.workflow_name, "status": run_status.status})
    
    # Then, include historical runs from SQLite
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT task_id, timestamp FROM task_memory ORDER BY timestamp DESC LIMIT ?", 
                (limit,)
            )
            rows = cursor.fetchall()
            for r in rows:
                results.append({"task_id": r[0], "timestamp": r[1], "status": "completed"})
    except Exception:
        pass
    
    return APIResponse(success=True, message=f"Found {len(results)} run(s)", data=results)

@router.get("/{task_id}", summary="Get run details", description="Returns the status and steps of a specific workflow run.")
def get_run_details(task_id: str):
    # Check in-memory store first (for async runs)
    run_store = get_run_store()
    if task_id in run_store:
        return APIResponse(success=True, message="Run found", data=run_store[task_id].model_dump())
    
    # Otherwise check SQLite journal
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        
        with sqlite3.connect(store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_id, step_id, action, provider, status, output, timestamp
                FROM execution_journal
                WHERE task_id = ?
                ORDER BY id ASC
            ''', (task_id,))
            
            rows = cursor.fetchall()
            if not rows:
                return APIResponse(
                    success=False, 
                    message="Run not found",
                    error=APIError(code="not_found", details=f"No run with task_id '{task_id}'", retryable=False)
                )
            
            journal = [dict(r) for r in rows]
            return APIResponse(success=True, message="Run journal found", data=journal)
            
    except Exception as e:
        return APIResponse(
            success=False,
            message="Failed to retrieve run",
            error=APIError(code="internal_error", details=str(e), retryable=False)
        )
