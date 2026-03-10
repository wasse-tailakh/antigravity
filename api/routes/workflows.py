import time
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.schemas import RunWorkflowRequest, APIResponse, APIError, RunStatusResponse
from api.services import execute_workflow_background, get_run_store

router = APIRouter()

@router.get("/", summary="List workflows", description="Returns all available workflow names.")
def list_workflows():
    workflows = [
        {"name": "project-update", "description": "Analyzes a target file and applies a requested refactor.", "required_args": ["target", "goal"]},
        {"name": "research", "description": "Scans a target directory, summarizes content based on a goal/topic.", "required_args": ["goal"]},
        {"name": "debug", "description": "Reads an error traceback and patches the target file.", "required_args": ["target", "error"]},
        {"name": "devops", "description": "Safely executes system shell commands to achieve a goal.", "required_args": ["goal"]},
        {"name": "continuation", "description": "Chains tasks from SQLite memory context.", "required_args": ["task_id", "goal"]},
    ]
    return APIResponse(success=True, message="Available workflows", data=workflows)

@router.post("/run", summary="Run a workflow", description="Starts a workflow execution asynchronously and returns a task_id for polling.")
def execute_workflow(req: RunWorkflowRequest, background_tasks: BackgroundTasks):
    workflow = req.workflow_name
    valid_workflows = ["project-update", "research", "debug", "devops", "continuation"]
    
    if workflow not in valid_workflows:
        return APIResponse(
            success=False,
            message=f"Workflow '{workflow}' not found",
            error=APIError(code="not_found", details=f"Available workflows: {', '.join(valid_workflows)}", retryable=False)
        )
    
    # Validate required arguments
    if workflow == "project-update" and (not req.target or not req.goal):
        return APIResponse(success=False, message="Missing arguments", error=APIError(code="validation_error", details="'project-update' requires 'target' and 'goal'", retryable=False))
    elif workflow == "research" and not req.goal:
        return APIResponse(success=False, message="Missing arguments", error=APIError(code="validation_error", details="'research' requires 'goal'", retryable=False))
    elif workflow == "debug" and (not req.target or not req.error):
        return APIResponse(success=False, message="Missing arguments", error=APIError(code="validation_error", details="'debug' requires 'target' and 'error'", retryable=False))
    elif workflow == "devops" and not req.goal:
        return APIResponse(success=False, message="Missing arguments", error=APIError(code="validation_error", details="'devops' requires 'goal'", retryable=False))
    elif workflow == "continuation" and (not req.task_id or not req.goal):
        return APIResponse(success=False, message="Missing arguments", error=APIError(code="validation_error", details="'continuation' requires 'task_id' and 'goal'", retryable=False))
    
    # Generate a unique task_id and register it as pending
    task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    run_store = get_run_store()
    run_store[task_id] = RunStatusResponse(
        task_id=task_id,
        workflow_name=workflow,
        status="pending"
    )
    
    # Launch in background
    background_tasks.add_task(execute_workflow_background, task_id, req)
    
    return APIResponse(
        success=True,
        message=f"Workflow '{workflow}' started. Poll GET /runs/{task_id} for status.",
        data={"task_id": task_id, "status": "pending"}
    )
