from typing import Any, Dict
from openai import OpenAI
from .base_agent import BaseAgent
from config.settings import settings
import json
from tools.tool_registry import ToolRegistry

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

    def run(self, prompt: str, context: Dict[str, Any] = None, tools_registry: ToolRegistry = None) -> str:
        self.logger.debug(f"Input context: {context}")
        if not self.client:
            return "Error: OpenAI client is not initialized (missing or invalid API key)."
            
        messages = []
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
        messages.append({"role": "user", "content": prompt})
            
        kwargs = {
            "model": self.model,
            "messages": messages
        }
        
        if tools_registry:
             kwargs["tools"] = tools_registry.get_openai_tools()
             
        try:
            self.logger.info("Starting OpenAI execution loop...")
            while True:
                response = self.client.chat.completions.create(**kwargs)
                response_message = response.choices[0].message
                
                # Check if the model wants to call a tool
                if not response_message.tool_calls:
                    self.logger.debug("Execution loop complete. Returning text.")
                    return response_message.content
                    
                # Append assistant message with tool calls
                messages.append(response_message)
                
                # Execute tools
                for tool_call in response_message.tool_calls:
                     function_name = tool_call.function.name
                     self.logger.info(f"OpenAI invoking tool: {function_name}")
                     
                     if tools_registry:
                         try:
                             function_args = json.loads(tool_call.function.arguments)
                             result = tools_registry.execute_tool(function_name, **function_args)
                             tool_response = str(result["output"]) if result["success"] else str(result["error"])
                         except Exception as e:
                             tool_response = f"Error parsing or executing tool arguments: {e}"
                             
                         messages.append({
                             "role": "tool",
                             "tool_call_id": tool_call.id,
                             "name": function_name,
                             "content": tool_response
                         })
                     else:
                          messages.append({
                             "role": "tool",
                             "tool_call_id": tool_call.id,
                             "name": function_name,
                             "content": "Tool registry not explicitly provided."
                         })
                         
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return f"Error from OpenAI processor: {e}"
