from typing import Any, Dict
from pathlib import Path
from .base_agent import BaseAgent
from .claude_agent import ClaudeAgent
from .openai_agent import OpenAIAgent
from .gemini_agent import GeminiAgent

class RouterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Orchestrator Router",
            capabilities=["routing", "delegation"]
        )
        # In a real system, the Router would likely use a fast LLM (like OpenAI mini) 
        # to analyze the prompt and pick the right agent. 
        # For this MVP, we initialize the available agents.
        self.agents = {
            "claude": ClaudeAgent(),
            "openai": OpenAIAgent(),
            "gemini": GeminiAgent()
        }
        
        # Load prompt safely
        prompt_path = Path(__file__).parent.parent / "prompts" / "router.txt"
        try:
            self.base_prompt = prompt_path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.warning(f"Could not load router prompt: {e}")
            self.base_prompt = "Respond with 'gemini' for anything not complex code."

    def run(self, prompt: str, context: Dict[str, Any] = None, tools_registry: Any = None) -> Any:
        # MVP Logic: Use Gemini to classify the intent and pick an agent (cheap)
        self.logger.info("Routing new task...")
        classification_prompt = self.base_prompt.format(prompt=prompt)
        
        try:
            self.logger.debug("Asking Gemini to classify intent.")
            decision = self.agents["gemini"].run(classification_prompt).strip().lower()
        except Exception as e:
            self.logger.warning(f"Failed to classify intent using Gemini: {e}. Falling back to gemini.")
            decision = "gemini"
            
        if decision not in self.agents:
            self.logger.warning(f"Invalid agent choice '{decision}', falling back to gemini.")
            decision = "gemini"
            
        self.logger.info(f"Delegating task to {decision.upper()} agent...")
        selected_agent = self.agents[decision]
        
        try:
            # Pass the tools registry down to the selected agent
            return selected_agent.run(prompt, context=context, tools_registry=tools_registry)
        except Exception as e:
            self.logger.error(f"Selected agent {decision.upper()} failed to run: {e}", exc_info=True)
            return f"Error in Router executing agent {decision.upper()}: {e}"
