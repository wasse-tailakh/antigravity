import os
from orchestrator.planner import Planner
from agents.router_agent import RouterAgent
from tools.tool_registry import ToolRegistry
from skills.file_skill import FileSkill
from skills.shell_skill import ShellSkill
from skills.git_skill import GitSkill
from config.logger import get_logger

class Executor:
    def __init__(self):
        self.logger = get_logger("Executor")
        self.planner = Planner()
        self.router = RouterAgent()
        
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
        context = {"plan": plan, "results_so_far": []}
        final_results = []
        
        for step in plan:
            step_id = step.get('id')
            desc = step.get('description')
            preferred_agent = step.get('agent_type', 'claude').lower()
            
            self.logger.info(f"Executing step {step_id}: {desc}")
            
            try:
                # Pass the tool registry down to the agents
                if preferred_agent in self.router.agents:
                     agent = self.router.agents[preferred_agent]
                     result = agent.run(desc, context=context, tools_registry=self.tool_registry)
                else:
                     result = self.router.run(desc, context=context, tools_registry=self.tool_registry)
                
                log_res = result[:200] + "..." if len(result) > 200 else result
                self.logger.info(f"Step {step_id} Result: {log_res}")
                
                step_result = {"step": step_id, "description": desc, "result": result}
                context["results_so_far"].append(step_result)
                final_results.append(step_result)
                
            except Exception as e:
                self.logger.error(f"Failed to execute step {step_id}: {str(e)}", exc_info=True)
                break
                
        self.logger.info("Execution Complete.")
        return final_results

# Example usage if run directly
if __name__ == "__main__":
    executor = Executor()
    executor.execute_task("Analyze the README.md file and suggest 3 improvements.")
