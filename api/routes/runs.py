from fastapi import APIRouter, HTTPException
import sqlite3
from typing import List
from api.schemas import RunJournalSchema

router = APIRouter()

@router.get("/", response_model=List[dict])
def list_runs(limit: int = 5):
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        
        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT task_id, timestamp FROM task_memory ORDER BY timestamp DESC LIMIT ?", 
                (limit,)
            )
            runs = cursor.fetchall()
            return [{"task_id": r[0], "timestamp": r[1]} for r in runs]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}", response_model=List[RunJournalSchema])
def get_run_details(task_id: str):
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
                raise HTTPException(status_code=404, detail="Run not found in execution journal")
                
            return [RunJournalSchema(**dict(r)) for r in rows]
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
