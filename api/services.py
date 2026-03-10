from fastapi import APIRouter
from api.schemas import RunWorkflowResponse, StepResultSchema

def analyze_workflow_results(workflow_name: str, results: list) -> RunWorkflowResponse:
    if not results:
        return RunWorkflowResponse(
            workflow_name=workflow_name,
            status="FAILED",
            llm_calls_approx=0,
            tool_calls=0,
            retries=0,
            escalated_to_claude=False,
            final_output="No results generated. Check if Planner crashed."
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
            
        # Parse timestamp string back to datetime if needed, or assume object
        ts = r.get("timestamp")
        
        steps.append(StepResultSchema(
            step_id=r.get("step_id", "unknown"),
            action=action or "none",
            status=r.get("status", "unknown"),
            output=r.get("output", ""),
            timestamp=ts,
            provider_used=provider,
            attempts=attempts
        ))
        
    final_status = results[-1].get("status", "unknown")
    if results[-1].get("error"):
        final_status = "error"
        output = results[-1].get("error")
    else:
        output = results[-1].get("output", "Completed.")

    return RunWorkflowResponse(
        workflow_name=workflow_name,
        status=final_status,
        llm_calls_approx=llm_calls,
        tool_calls=tool_calls,
        retries=retries,
        escalated_to_claude=escalated,
        final_output=output,
        steps=steps
    )
