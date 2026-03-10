from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/health")
def return_health():
    return {"status": "ok", "service": "antigravity"}

@router.get("/doctor")
def check_environment():
    keys = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    status_report = {}
    
    for k in keys:
        status_report[k] = "OK" if os.environ.get(k) else "FAIL"
        
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        status_report["SQLite"] = "OK"
    except Exception as e:
        status_report["SQLite"] = f"FAIL: {str(e)}"
        
    return {
        "status": "healthy" if status_report["SQLite"] == "OK" else "degraded",
        "doctor": status_report
    }
