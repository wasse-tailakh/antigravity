from agents.router_agent import RouterAgent
from config.logger import get_logger
from memory.response_cache import response_cache
from orchestrator.backoff import BackoffLogic
from policies.rate_limit_policy import RateLimitPolicy
from pathlib import Path
from typing import List, Dict, Any
import json
import re

class Planner:
    def __init__(self):
        self.router = RouterAgent()
        self.logger = get_logger("Planner")
        self.rate_limit_policy = RateLimitPolicy()
        
        # Load prompt safely
        prompt_path = Path(__file__).parent.parent / "prompts" / "planner.txt"
        try:
            self.base_prompt = prompt_path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.warning(f"Could not load planner prompt: {e}")
            self.base_prompt = "Format output as JSON list of tasks."
        
    def create_plan(self, task_description: str, memory_context: str = "") -> List[Dict[str, Any]]:
        """
        Takes a complex user request and breaks it down into actionable steps.
        """
        self.logger.info("Developing execution plan...")
        
        # We explicitly route this to Claude for high-quality planning
        planning_prompt = f"""
        Break down the following user request into a sequence of concrete, actionable steps.
        
        Request: "{task_description}"
        
        RECENT TASK MEMORY (Context from previous operations):
        {memory_context}
        
        Available capabilities:
        - file operations (read/write)
        - shell execution (running commands)
        - git operations (clone, commit, push)
        - web research
        - code writing/modification
        
        Format the output as a JSON block with a list of tasks. Each task should have:
        - id: a step number
        - description: clear description of what needs to be done
        - agent_type: which agent should handle it (claude, openai, or gemini)
        
        Respond ONLY with the raw JSON array. Ex: [{{ "id": 1, "description": "...", "agent_type": "gemini" }}]
        """
        
        def _compute_plan():
            def _llm_call():
                self.logger.debug("Calling Gemini for planning...")
                return self.router.agents["gemini"].run(planning_prompt)
                
            response_text = BackoffLogic.execute_with_backoff(
                operation=_llm_call,
                max_attempts=3,
                base_delay=2.0,
                max_delay=60.0,
                rate_limit_policy=self.rate_limit_policy
            )
            
            # Extract JSON from potential markdown formatting or conversational wrapper
            import json
            import re
            
            # Try to find a JSON array block
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
               json_str = json_match.group(1)
            else:
               # Try to find just an array if no codeblocks
               array_match = re.search(r'(\[.*?\])', response_text, re.DOTALL)
               if array_match:
                   json_str = array_match.group(1)
               else:
                   json_str = response_text
               
            plan = json.loads(json_str)
            self.logger.info(f"Successfully created a plan with {len(plan)} steps.")
            return plan

        try:
            return response_cache.get_or_compute(
                namespace="planner",
                payload={"task": task_description, "memory": memory_context},
                compute_fn=_compute_plan
            )
        except Exception as e:
            self.logger.error(f"Error generating plan: {str(e)}", exc_info=True)
            # Fallback to a single-step plan
            return [{"id": 1, "description": task_description, "agent_type": "gemini"}]

