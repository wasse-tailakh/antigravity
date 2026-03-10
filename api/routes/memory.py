from fastapi import APIRouter, HTTPException
import sqlite3
from typing import List
from api.schemas import TaskSummarySchema

router = APIRouter()

@router.get("/recent", response_model=List[TaskSummarySchema])
def get_recent_memory(limit: int = 5):
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        summaries = store.get_recent_task_summaries(limit=limit)
        
        # Mapping to Pydantic schemas natively
        results = []
        for s in summaries:
            results.append(TaskSummarySchema(
                task_id=s.get("task_id"),
                user_prompt=s.get("user_prompt"),
                summary=s.get("summary"),
                timestamp=s.get("timestamp"),
                metadata=s.get("metadata", {})
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}", response_model=TaskSummarySchema)
def get_task_memory(task_id: str):
    try:
        from memory.memory_store import SQLiteMemoryStore
        import json
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
                raise HTTPException(status_code=404, detail="Task memory not found")
                
            r_dict = dict(row)
            r_dict['metadata'] = json.loads(r_dict.pop('metadata_json', "{}"))
            
            return TaskSummarySchema(**r_dict)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
