from typing import Any, Dict
import google.genai as genai
from .base_agent import BaseAgent
from config.settings import settings

class GeminiAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Gemini Explorer",
            capabilities=["web", "vision", "files_analysis"]
        )
        self.model = 'gemini-2.5-flash'
        try:
            self.client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as e:
            self.logger.warning(f"Failed to initialize Gemini client: {e}")
            self.client = None

    def run(self, prompt: str, context: Dict[str, Any] = None) -> str:
        self.logger.debug(f"Input context: {context}")
        if not self.client:
            return "Error: Gemini client is not initialized (missing or invalid API key)."
        prompt_parts = [prompt]
        if context:
            prompt_parts.insert(0, f"Context: {context}")
            
        try:
            self.logger.info("Calling Gemini API...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt_parts,
            )
            self.logger.debug("Successfully generated response from Gemini.")
            return response.text
        except Exception as e:
            self.logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            return f"Error from Gemini explorer: {e}"
