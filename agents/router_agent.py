from typing import Any, Dict
from pathlib import Path
from .base_agent import BaseAgent
from .claude_agent import ClaudeAgent
from .openai_agent import OpenAIAgent
from .gemini_agent import GeminiAgent
from memory.response_cache import response_cache
from orchestrator.backoff import BackoffLogic
from policies.rate_limit_policy import RateLimitPolicy

class RouterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Orchestrator Router",
            capabilities=["routing", "delegation"]
        )
        # Lazy-loaded agent registry — agents are only instantiated on first use
        self._agents = {}
        self._agent_classes = {
            "claude": ClaudeAgent,
            "openai": OpenAIAgent,
            "gemini": GeminiAgent
        }
        self.rate_limit_policy = RateLimitPolicy()
        
        # Load prompt safely
        prompt_path = Path(__file__).parent.parent / "prompts" / "router.txt"
        try:
            self.base_prompt = prompt_path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.warning(f"Could not load router prompt: {e}")
            self.base_prompt = "Respond with 'gemini' for anything not complex code."

    @property
    def agents(self):
        """Lazy-loading property — instantiates agents only on first access."""
        return self._agents
    
    def get_agent(self, name: str):
        """Get or create an agent by name."""
        if name not in self._agents:
            cls = self._agent_classes.get(name)
            if cls:
                self.logger.info(f"Lazy-loading {name} agent...")
                self._agents[name] = cls()
            else:
                raise ValueError(f"Unknown agent: {name}")
        return self._agents[name]

    def run(self, prompt: str, context: Dict[str, Any] = None, tools_registry: Any = None) -> Any:
        # MVP Logic: Use Gemini to classify the intent and pick an agent (cheap)
        self.logger.info("Routing new task...")
        classification_prompt = self.base_prompt.format(prompt=prompt)
        
        def _compute_routing():
            def _llm_call():
                self.logger.debug("Asking Gemini to classify intent.")
                return self.get_agent("gemini").run(classification_prompt)
                
            return BackoffLogic.execute_with_backoff(
                operation=_llm_call,
                max_attempts=3,
                base_delay=2.0,
                max_delay=60.0,
                rate_limit_policy=self.rate_limit_policy
            ).strip().lower()

        try:
            decision = response_cache.get_or_compute(
                namespace="router",
                payload={"prompt": prompt},
                compute_fn=_compute_routing
            )
        except Exception as e:
            self.logger.warning(f"Failed to classify intent using Gemini: {e}. Falling back to gemini.")
            decision = "gemini"
            
        if decision not in self._agent_classes:
            self.logger.warning(f"Invalid agent choice '{decision}', falling back to gemini.")
            decision = "gemini"
            
        self.logger.info(f"Delegating task to {decision.upper()} agent...")
        selected_agent = self.get_agent(decision)
        
        try:
            # Pass the tools registry down to the selected agent
            return selected_agent.run(prompt, context=context, tools_registry=tools_registry)
        except Exception as e:
            self.logger.error(f"Selected agent {decision.upper()} failed to run: {e}", exc_info=True)
            return f"Error in Router executing agent {decision.upper()}: {e}"
