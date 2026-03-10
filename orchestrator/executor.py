import os
import time
from typing import Any

from orchestrator.planner import Planner
from agents.router_agent import RouterAgent
from tools.tool_registry import ToolRegistry
from skills.file_skill import FileSkill
from skills.shell_skill import ShellSkill
from skills.git_skill import GitSkill
from config.logger import get_logger

from orchestrator.execution_state import ExecutionState, StepResult
from orchestrator.retry_policy import RetryPolicy, FailureCategory
from orchestrator.reviewer import Reviewer
from orchestrator.backoff import BackoffLogic
from policies.cost_guard import CostGuard, TaskCostState
from policies.rate_limit_policy import RateLimitPolicy

class Executor:
    def __init__(self):
        self.logger = get_logger("Executor")
        self.planner = Planner()
        self.router = RouterAgent()
        self.retry_policy = RetryPolicy(max_attempts=3)
        self.cost_guard = CostGuard()
        self.rate_limit_policy = RateLimitPolicy()
        self.reviewer = Reviewer()
        
        # Initialize Tool Registry
        self.tool_registry = ToolRegistry()
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # Register tools
        self.tool_registry.register(FileSkill(project_root=project_root))
        self.tool_registry.register(ShellSkill())
        self.tool_registry.register(GitSkill())
        
        self.logger.info("Executor initialized with ToolRegistry.")
        
    def execute_task(self, user_request: str):
        self.logger.info(f"New Task Received: {user_request}")
        
        # 1. Planning Phase
        try:
            plan = self.planner.create_plan(user_request)
        except Exception as e:
            self.logger.critical(f"Planner failed critically: {e}", exc_info=True)
            return []
        
        self.logger.info("--- Execution Plan ---")
        for step in plan:
            self.logger.info(f"Step {step.get('id', '?')}: {step.get('description', 'Unknown')} (Agent: {step.get('agent_type', 'router')})")
        
        # 2. Execution Phase
        task_id = f"task_{int(time.time())}"
        state = ExecutionState(task_id=task_id, user_prompt=user_request, steps=plan)
        budget = TaskCostState(task_id=task_id)
        
        while not state.is_complete():
            step = state.current_step()
            if not step:
                break
                
            step_id = step.get('id', 'unknown')
            desc = step.get('description', '')
            preferred_agent = step.get('agent_type', 'gemini').lower()
            
            self.logger.info(f"Executing step {step_id}: {desc}")
            
            attempts = 0
            final_result = None
            current_prompt = desc
            
            while attempts < self.retry_policy.max_attempts:
                attempts += 1
                
                # Check limits
                allowed, reason = self.cost_guard.can_call_llm(budget, preferred_agent)
                if not allowed:
                    final_result = StepResult(step_id=str(step_id), status="failed", error=reason, attempts=attempts)
                    break
                    
                budget.record_llm_call(provider=preferred_agent)
                
                # Optimize context: only send minimal previous step result, not the whole history
                minimal_context = {"step": desc}
                last_res = state.last_result()
                if last_res:
                    minimal_context["last_step_output"] = last_res.output
                    
                def _llm_call():
                     if preferred_agent in self.router.agents:
                          agent = self.router.agents[preferred_agent]
                          return agent.run(current_prompt, context=minimal_context, tools_registry=self.tool_registry)
                     return self.router.run(current_prompt, context=minimal_context, tools_registry=self.tool_registry)

                try:
                     agent_output = BackoffLogic.execute_with_backoff(
                         operation=_llm_call,
                         max_attempts=3,
                         base_delay=2.0,
                         max_delay=60.0,
                         rate_limit_policy=self.rate_limit_policy
                     )
                     
                     temp_result = StepResult(step_id=str(step_id), status="success", output=agent_output, provider_used=preferred_agent, attempts=attempts)
                     ok, review_msg = self.reviewer.review_step(step, temp_result)
                     
                except Exception as e:
                     self.logger.error(f"Failed to execute step {step_id} on attempt {attempts}: {str(e)}")
                     temp_result = StepResult(step_id=str(step_id), status="failed", error=str(e), provider_used=preferred_agent, attempts=attempts)
                     ok, review_msg = False, str(e)
                     
                if ok:
                    self.logger.info(f"Step {step_id} executed and validated successfully on attempt {attempts}.")
                    temp_result.metadata["review"] = review_msg
                    final_result = temp_result
                    break
                    
                # Validation or execution failed
                self.logger.warning(f"Step {step_id} failed on attempt {attempts}. Feedback: {review_msg}")
                temp_result.status = "failed"
                temp_result.error = review_msg
                
                # Ask RetryPolicy what to do
                retry_decision = self.retry_policy.decide(temp_result.error, attempts)
                
                if retry_decision.should_retry:
                    self.logger.info(f"Retry Decision: {retry_decision.reason}. Retrying...")
                    
                    if retry_decision.should_escalate and preferred_agent != "claude":
                        self.logger.warning(f"Escalating task {step_id} from {preferred_agent} to claude due to repeated failures.")
                        preferred_agent = "claude"
                        budget.escalated_to_claude = True
                        
                    current_prompt = f"Previous attempt failed. Feedback from Reviewer: {review_msg}\n\nPlease analyze the feedback and try a different approach to fulfill the original request: {desc}"
                    
                    if retry_decision.delay_seconds > 0:
                        time.sleep(retry_decision.delay_seconds)
                    continue
                    
                self.logger.error(f"Retry Decision: {retry_decision.reason}. Halting retries for step {step_id}.")
                temp_result.metadata["review"] = review_msg
                temp_result.metadata["failure_category"] = retry_decision.category.name if retry_decision.category else "UNKNOWN"
                final_result = temp_result
                break

            # Fallback if final_result is somehow still None (e.g. max attempts reached without setting it correctly in loop)
            if not final_result:
                 final_result = StepResult(step_id=str(step_id), status="failed", error="Unknown execution failure without distinct result.", attempts=attempts)

            state.add_result(final_result)
            
            # Fast fail if a step completely failed to prevent cascading errors
            if final_result.status == "failed":
                self.logger.error(f"Halting execution plan due to permanent failure in step {step_id}.")
                break
                
            state.advance()
                
        self.logger.info("Execution Complete.")
        # Return dictionaries to match earlier behavior for callers
        return [r.__dict__ for r in state.results]

# Example usage if run directly
if __name__ == "__main__":
    executor = Executor()
    executor.execute_task("Analyze the README.md file and suggest 3 improvements.")

