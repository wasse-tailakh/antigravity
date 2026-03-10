from typing import Any, Dict
from openai import OpenAI
from .base_agent import BaseAgent
from config.settings import settings

class OpenAIAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="OpenAI Processor",
            capabilities=["classification", "transformation", "summarization", "fast_execution"]
        )
        self.model = "gpt-4o-mini"
        try:
            self.client = OpenAI(api_key=settings.openai_api_key)
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.client = None

    def run(self, prompt: str, context: Dict[str, Any] = None) -> str:
        self.logger.debug(f"Input context: {context}")
        if not self.client:
            return "Error: OpenAI client is not initialized (missing or invalid API key)."
        messages = [{"role": "user", "content": prompt}]
        if context:
            messages.insert(0, {"role": "system", "content": f"Context: {context}"})
            
        try:
            self.logger.info("Calling OpenAI API...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            self.logger.debug("Successfully generated response from OpenAI.")
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return f"Error from OpenAI processor: {e}"
