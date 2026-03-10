from typing import Any, Dict
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

    def run(self, prompt: str, context: Dict[str, Any] = None, tools_registry: Any = None) -> Any:
        # MVP Logic: Use Claude to classify the intent and pick an agent
        self.logger.info("Routing new task...")
        classification_prompt = f"""
        Analyze this request: "{prompt}"
        Which agent is best suited for it?
        Options:
        - claude: Complex planning, architecture, writing code
        - openai: Simple tasks, fast text transformation, summarization
        - gemini: Tasks involving analyzing files, web content, or vision
        
        Respond with ONLY the name of the agent (claude, openai, or gemini).
        """
        
        try:
            self.logger.debug("Asking Claude to classify intent.")
            decision = self.agents["claude"].run(classification_prompt).strip().lower()
        except Exception as e:
            self.logger.warning(f"Failed to classify intent using Claude: {e}. Falling back to claude.")
            decision = "claude"
            
        if decision not in self.agents:
            self.logger.warning(f"Invalid agent choice '{decision}', falling back to claude.")
            decision = "claude"
            
        self.logger.info(f"Delegating task to {decision.upper()} agent...")
        selected_agent = self.agents[decision]
        
        try:
            # Pass the tools registry down to the selected agent
            return selected_agent.run(prompt, context=context, tools_registry=tools_registry)
        except Exception as e:
            self.logger.error(f"Selected agent {decision.upper()} failed to run: {e}", exc_info=True)
            return f"Error in Router executing agent {decision.upper()}: {e}"
