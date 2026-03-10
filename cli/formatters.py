import sys

def print_banner():
    print("="*60)
    print("[ANTIGRAVITY CLI]")
    print("="*60)

def print_workflow_result(workflow_name: str, results: list):
    """Extracts stats from the step results and formats a gorgeous output block."""
    print(f"\nWorkflow: {workflow_name}")
    
    if not results:
        print("Status: FAILED (No results generated. Check if Planner crashed immediately.)")
        return
        
    llm_calls = 0
    tool_calls = 0
    retries = 0
    providers = set()
    escalated = False
    
    for r in results:
        llm_calls += 1 # Rough estimate, real count should come from CostGuard tracing
        providers.add(r.get("provider_used", "unknown"))
        if r.get("provider_used") == "claude":
            escalated = True
        
        attempts = r.get("attempts", 1)
        if attempts > 1:
            retries += (attempts - 1)
            
        action = r.get("action")
        if action and action != "none":
            tool_calls += 1
            
    # Assuming memory hits aren't explicitly tracked in step results yet, we mock or infer it.
    # In a real impl, CostGuard or ExecutionState would hold this exact metric.
    
    # The last step status is usually the final outcome
    final_status = results[-1].get("status", "unknown")
    if results[-1].get("error"):
        final_status = "error"
        output = results[-1].get("error")
    else:
        output = results[-1].get("output", "Completed.")
        
    print(f"Provider: {', '.join(providers)}")
    print(f"Escalated to Claude: {'yes' if escalated else 'no'}")
    print(f"LLM calls: {llm_calls} (approx)")
    print(f"Tool calls: {tool_calls}")
    print(f"Retries: {retries}")
    print(f"Status: {final_status}")
    print("-" * 60)
    print("Output:")
    print(str(output).strip()[:500] + ("..." if len(str(output)) > 500 else ""))
    print("=" * 60)

def print_error(msg: str):
    print(f"❌ ERROR: {msg}")
    sys.exit(1)
