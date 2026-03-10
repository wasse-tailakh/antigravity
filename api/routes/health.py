from fastapi import APIRouter
import os
from api.schemas import APIResponse

router = APIRouter()

@router.get("/health", summary="Health check", description="Returns a simple OK status to confirm the API is running.")
def return_health():
    return APIResponse(success=True, message="API is healthy", data={"status": "ok", "service": "antigravity"})

@router.get("/doctor", summary="Environment diagnostics", description="Checks API keys and SQLite database writability.")
def check_environment():
    keys = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    status_report = {}
    
    for k in keys:
        status_report[k] = "OK" if os.environ.get(k) else "MISSING"
        
    try:
        from memory.memory_store import SQLiteMemoryStore
        store = SQLiteMemoryStore()
        status_report["SQLite"] = "OK"
    except Exception as e:
        status_report["SQLite"] = f"FAIL: {str(e)}"
    
    overall = "healthy" if status_report["SQLite"] == "OK" else "degraded"
    return APIResponse(success=True, message=f"System is {overall}", data={"status": overall, "checks": status_report})
