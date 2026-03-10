import os
from orchestrator.planner import Planner
from agents.router_agent import RouterAgent
from tools.tool_registry import ToolRegistry
from skills.file_skill import FileSkill
from skills.shell_skill import ShellSkill
from skills.git_skill import GitSkill
from config.logger import get_logger
from orchestrator.execution_state import ExecutionStatus, TaskResult
from orchestrator.retry_policy import RetryPolicy
from orchestrator.reviewer import Reviewer
from policies.cost_guard import CostGuard

class Executor:
    def __init__(self):
        self.logger = get_logger("Executor")
        self.planner = Planner()
        self.router = RouterAgent()
        self.retry_policy = RetryPolicy()
        self.cost_guard = CostGuard()
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
        self.cost_guard.reset()
        context = {"plan": plan, "results_so_far": []}
        final_results = []
        
        for step in plan:
            step_id = step.get('id')
            desc = step.get('description')
            preferred_agent = step.get('agent_type', 'claude').lower()
            
            self.logger.info(f"Executing step {step_id}: {desc}")
            
            task_result = TaskResult(step_id=step_id, description=desc)
            attempts = 0
            success = False
            current_prompt = desc
            
            while attempts < self.retry_policy.max_attempts and not success:
                attempts += 1
                task_result.attempts = attempts
                task_result.status = ExecutionStatus.RUNNING
                
                try:
                    # Cost Guard Check
                    if not self.cost_guard.log_llm_call():
                        task_result.status = ExecutionStatus.FAILED
                        task_result.error = "CostGuard threshold exceeded."
                        task_result.output = agent_output if 'agent_output' in locals() else None
                        break
                        
                    # Optimize context: only send minimal previous step result, not the whole history
                    minimal_context = {"step": desc}
                    if len(context["results_so_far"]) > 0:
                        last_result = context["results_so_far"][-1]
                        minimal_context["last_step_output"] = last_result.get("output")
                        
                    # Pass the tool registry down to the agents
                    if preferred_agent in self.router.agents:
                         agent = self.router.agents[preferred_agent]
                         agent_output = agent.run(current_prompt, context=minimal_context, tools_registry=self.tool_registry)
                    else:
                         agent_output = self.router.run(current_prompt, context=minimal_context, tools_registry=self.tool_registry)
                    
                    # Review the step output
                    review = self.reviewer.review_step(task_description=desc, agent_output=agent_output)
                    
                    if review.is_valid:
                        self.logger.info(f"Step {step_id} executed and validated successfully on attempt {attempts}.")
                        success = True
                        task_result.status = ExecutionStatus.SUCCESS
                        task_result.output = agent_output
                    else:
                        self.logger.warning(f"Step {step_id} failed review on attempt {attempts}. Feedback: {review.feedback}")
                        if self.retry_policy.should_retry(attempts, review.feedback):
                            task_result.status = ExecutionStatus.NEEDS_RETRY
                            current_prompt = f"Previous attempt failed. Feedback: {review.feedback}\n\nPlease try again to fulfill the original request: {desc}"
                            self.retry_policy.wait_for_retry(attempts)
                        else:
                            task_result.status = ExecutionStatus.FAILED
                            task_result.error = review.feedback
                            task_result.output = agent_output
                            break
                            
                except Exception as e:
                    self.logger.error(f"Failed to execute step {step_id} on attempt {attempts}: {str(e)}", exc_info=True)
                    if self.retry_policy.should_retry(attempts, str(e)):
                        task_result.status = ExecutionStatus.NEEDS_RETRY
                        self.retry_policy.wait_for_retry(attempts)
                    else:
                        task_result.status = ExecutionStatus.FAILED
                        task_result.error = str(e)
                        break

            # Append the structured result
            step_dict = task_result.model_dump()
            context["results_so_far"].append(step_dict)
            final_results.append(step_dict)
            
            # Fast fail if a step completely failed to prevent cascading errors
            if task_result.status == ExecutionStatus.FAILED:
                self.logger.error(f"Halting execution plan due to failure in step {step_id}.")
                break
                
        self.logger.info("Execution Complete.")
        return final_results

# Example usage if run directly
if __name__ == "__main__":
    executor = Executor()
    executor.execute_task("Analyze the README.md file and suggest 3 improvements.")
