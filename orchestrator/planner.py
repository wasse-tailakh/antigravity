from agents.router_agent import RouterAgent
from config.logger import get_logger
from typing import List, Dict, Any
import json
import re

class Planner:
    def __init__(self):
        self.router = RouterAgent()
        self.logger = get_logger("Planner")
        
    def create_plan(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Takes a complex user request and breaks it down into actionable steps.
        """
        self.logger.info("Developing execution plan...")
        
        # We explicitly route this to Claude for high-quality planning
        planning_prompt = f"""
        Break down the following user request into a sequence of concrete, actionable steps.
        
        Request: "{task_description}"
        
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
        
        try:
            # Bypass router classification, force claude for planning
            self.logger.debug("Calling Claude for planning...")
            response_text = self.router.agents["claude"].run(planning_prompt)
        except Exception as e:
            self.logger.error(f"Failed to get plan from Claude: {e}", exc_info=True)
            return [{"id": 1, "description": task_description, "agent_type": "claude"}]
        
        try:
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
        except Exception as e:
            self.logger.error(f"Error parsing plan: {str(e)}\nRaw response: {response_text}", exc_info=True)
            # Fallback to a single-step plan
            return [{"id": 1, "description": task_description, "agent_type": "claude"}]
