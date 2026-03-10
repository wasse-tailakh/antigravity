from fastapi import APIRouter, HTTPException
from api.schemas import RunWorkflowRequest, RunWorkflowResponse
from api.services import analyze_workflow_results
from workflows.project_update import run_project_update_workflow
from workflows.research_summary import run_research_workflow
from workflows.debugging import run_debugging_workflow
from workflows.devops import run_devops_workflow
from workflows.continuation import run_continuation_workflow

router = APIRouter()

@router.get("/")
def list_workflows():
    return {
        "workflows": [
            "project-update",
            "research",
            "debug",
            "devops",
            "continuation"
        ]
    }

@router.post("/run", response_model=RunWorkflowResponse)
def execute_workflow(req: RunWorkflowRequest):
    workflow = req.workflow_name
    results = None
    
    try:
        if workflow == "project-update":
            if not req.target or not req.goal:
                raise HTTPException(status_code=400, detail="Workflow 'project-update' requires 'target' and 'goal'")
            results = run_project_update_workflow(req.target, req.goal)
            
        elif workflow == "research":
            if not req.goal:
                raise HTTPException(status_code=400, detail="Workflow 'research' requires 'goal' (topic)")
            target_dir = req.target or "."
            results = run_research_workflow(req.goal, target_dir)
            
        elif workflow == "debug":
            if not req.target or not req.error:
                raise HTTPException(status_code=400, detail="Workflow 'debug' requires 'target' and 'error' (traceback)")
            results = run_debugging_workflow(req.error, req.target)
            
        elif workflow == "devops":
            if not req.goal:
                raise HTTPException(status_code=400, detail="Workflow 'devops' requires 'goal'")
            results = run_devops_workflow(req.goal)
            
        elif workflow == "continuation":
            if not req.task_id or not req.goal:
                raise HTTPException(status_code=400, detail="Workflow 'continuation' requires 'task_id' and 'goal'")
            results = run_continuation_workflow(req.task_id, req.goal)
            
        else:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow}' not found")
            
        return analyze_workflow_results(workflow, results)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
