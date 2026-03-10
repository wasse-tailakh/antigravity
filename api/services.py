import time
from datetime import datetime
from api.schemas import RunWorkflowRequest, RunStatusResponse, StepResultSchema

# In-memory store for background run statuses
# In production this would be Redis or a DB table
_run_store = {}

def get_run_store():
    return _run_store

def execute_workflow_background(task_id: str, req: RunWorkflowRequest):
    """
    Executes a workflow in the background. Updates the in-memory _run_store
    with progress and final results.
    """
    store = get_run_store()
    
    store[task_id] = RunStatusResponse(
        task_id=task_id,
        workflow_name=req.workflow_name,
        status="running",
        started_at=datetime.utcnow()
    )
    
    results = None
    
    try:
        from workflows.project_update import run_project_update_workflow
        from workflows.research_summary import run_research_workflow
        from workflows.debugging import run_debugging_workflow
        from workflows.devops import run_devops_workflow
        from workflows.continuation import run_continuation_workflow
        
        workflow = req.workflow_name
        
        if workflow == "project-update":
            results = run_project_update_workflow(req.target, req.goal)
        elif workflow == "research":
            results = run_research_workflow(req.goal, req.target or ".")
        elif workflow == "debug":
            results = run_debugging_workflow(req.error, req.target)
        elif workflow == "devops":
            results = run_devops_workflow(req.goal)
        elif workflow == "continuation":
            results = run_continuation_workflow(req.task_id, req.goal)
        
        # Analyze results
        analyzed = analyze_results(workflow, results)
        analyzed.task_id = task_id
        analyzed.started_at = store[task_id].started_at
        analyzed.finished_at = datetime.utcnow()
        store[task_id] = analyzed
        
    except Exception as e:
        store[task_id] = RunStatusResponse(
            task_id=task_id,
            workflow_name=req.workflow_name,
            status="failed",
            started_at=store[task_id].started_at,
            finished_at=datetime.utcnow(),
            final_output=str(e)
        )

def analyze_results(workflow_name: str, results: list) -> RunStatusResponse:
    if not results:
        return RunStatusResponse(
            task_id="",
            workflow_name=workflow_name,
            status="failed",
            final_output="No results generated."
        )

    llm_calls = 0
    tool_calls = 0
    retries = 0
    escalated = False
    steps = []
    
    for r in results:
        llm_calls += 1
        provider = r.get("provider_used", "unknown")
        if provider == "claude":
            escalated = True
            
        attempts = r.get("attempts", 1)
        if attempts > 1:
            retries += (attempts - 1)
            
        action = r.get("action")
        if action and action != "none":
            tool_calls += 1
            
        steps.append(StepResultSchema(
            step_id=r.get("step_id", "unknown"),
            action=action or "none",
            status=r.get("status", "unknown"),
            output=r.get("output", ""),
            timestamp=r.get("timestamp"),
            provider_used=provider,
            attempts=attempts
        ))
        
    final_status = results[-1].get("status", "unknown")
    if results[-1].get("error"):
        final_status = "failed"
        output = results[-1].get("error")
    else:
        final_status = "completed"
        output = results[-1].get("output", "Completed.")

    return RunStatusResponse(
        task_id="",
        workflow_name=workflow_name,
        status=final_status,
        llm_calls_approx=llm_calls,
        tool_calls=tool_calls,
        retries=retries,
        escalated_to_claude=escalated,
        final_output=output,
        steps=steps
    )
