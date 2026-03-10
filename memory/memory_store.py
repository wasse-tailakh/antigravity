import sqlite3
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from config.logger import get_logger

logger = get_logger("MemoryStore")

class SQLiteMemoryStore:
    """
    A simple SQLite-backed storage for long-term task memories and execution journals.
    Stores data in `.cache/memory.db` by default.
    """
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.db_path = os.path.join(project_root, ".cache", "memory.db")
        else:
            self.db_path = db_path
            
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table for Task Memory (High-level Summaries)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_memory (
                    task_id TEXT PRIMARY KEY,
                    user_prompt TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT
                )
            ''')
            
            # Table for Execution Journal (Detailed Steps)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    action TEXT,
                    provider TEXT,
                    status TEXT,
                    output TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES task_memory(task_id)
                )
            ''')
            conn.commit()

    def save_task_summary(self, task_id: str, prompt: str, summary: str, metadata: dict = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            meta_str = json.dumps(metadata) if metadata else "{}"
            cursor.execute('''
                INSERT OR REPLACE INTO task_memory (task_id, user_prompt, summary, metadata_json)
                VALUES (?, ?, ?, ?)
            ''', (task_id, prompt, summary, meta_str))
            conn.commit()
            logger.debug(f"Saved task summary for {task_id}")

    def get_recent_task_summaries(self, limit: int = 5) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_id, user_prompt, summary, timestamp, metadata_json
                FROM task_memory
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                r_dict = dict(row)
                r_dict['metadata'] = json.loads(r_dict.pop('metadata_json', "{}"))
                results.append(r_dict)
            return results

    def append_journal_entry(self, task_id: str, step_id: str, action: str, provider: str, status: str, output: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO execution_journal (task_id, step_id, action, provider, status, output)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task_id, step_id, action, provider, status, output))
            conn.commit()
