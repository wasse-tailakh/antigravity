from typing import Any, Dict
from anthropic import Anthropic
from .base_agent import BaseAgent
from config.settings import settings

class ClaudeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Claude Planner",
            capabilities=["planning", "architecture", "code_review"]
        )
        self.model = "claude-3-5-sonnet-20241022"
        try:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        except Exception as e:
            self.logger.warning(f"Failed to initialize Anthropic client: {e}")
            self.client = None

    def run(self, prompt: str, context: Dict[str, Any] = None) -> str:
        self.logger.debug(f"Input context: {context}")
        if not self.client:
            return "Error: Claude client is not initialized (missing or invalid API key)."
        messages = [{"role": "user", "content": prompt}]
        if context:
            messages.insert(0, {"role": "system", "content": f"Context: {context}"})
            
        try:
            self.logger.info("Calling Anthropic API...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=messages
            )
            self.logger.debug("Successfully generated response from Claude.")
            return response.content[0].text
        except Exception as e:
            self.logger.error(f"Error calling Claude API: {e}", exc_info=True)
            return f"Error from Claude planner: {e}"
