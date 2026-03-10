from fastapi import APIRouter
import sqlite3
import json
from typing import List
from api.schemas import APIResponse, APIError, TaskSummarySchema

router = APIRouter()

@router.get("/recent", summary="Recent task memories", description="Returns the latest task memory summaries from the SQLite store.")
def get_recent_memory(limit: int = 5):
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        summaries = store.get_recent_task_summaries(limit=limit)
        
        results = []
        for s in summaries:
            results.append(TaskSummarySchema(
                task_id=s.get("task_id"),
                user_prompt=s.get("user_prompt"),
                summary=s.get("summary"),
                timestamp=s.get("timestamp"),
                metadata=s.get("metadata", {})
            ))
        return APIResponse(success=True, message=f"Found {len(results)} memories", data=results)
    except Exception as e:
        return APIResponse(
            success=False,
            message="Failed to retrieve memory",
            error=APIError(code="internal_error", details=str(e), retryable=False)
        )

@router.get("/{task_id}", summary="Task memory by ID", description="Returns stored memory for a specific task ID.")
def get_task_memory(task_id: str):
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        
        with sqlite3.connect(store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_id, user_prompt, summary, timestamp, metadata_json
                FROM task_memory
                WHERE task_id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return APIResponse(
                    success=False,
                    message="Task memory not found",
                    error=APIError(code="not_found", details=f"No memory for task_id '{task_id}'", retryable=False)
                )
                
            r_dict = dict(row)
            r_dict['metadata'] = json.loads(r_dict.pop('metadata_json', "{}"))
            
            return APIResponse(success=True, message="Memory found", data=TaskSummarySchema(**r_dict))
            
    except Exception as e:
        return APIResponse(
            success=False,
            message="Failed to retrieve memory",
            error=APIError(code="internal_error", details=str(e), retryable=False)
        )
