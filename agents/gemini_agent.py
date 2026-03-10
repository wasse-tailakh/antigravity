from typing import Any, Dict
import google.genai as genai
from google.genai import types
from .base_agent import BaseAgent
from config.settings import settings
from tools.tool_registry import ToolRegistry

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

    def run(self, prompt: str, context: Dict[str, Any] = None, tools_registry: ToolRegistry = None) -> str:
        self.logger.debug(f"Input context: {context}")
        if not self.client:
            return "Error: Gemini client is not initialized (missing or invalid API key)."
            
        system_instruction = "You are Gemini, a helpful AI assistant."
        if context:
            system_instruction += f"\nContext: {context}"
            
        config_kwargs = {
            "system_instruction": system_instruction,
            "temperature": 0.0,
        }
        
        gemini_tools = None
        if tools_registry:
            gemini_tools = tools_registry.get_gemini_tools()
            if gemini_tools:
                config_kwargs["tools"] = [{"function_declarations": gemini_tools}]
        
        # We need to maintain a history for tool chat
        chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(**config_kwargs)
        )
        
        try:
            self.logger.info("Starting Gemini execution loop...")
            response = chat.send_message(prompt)
            
            while True:
                # Check for tool calls
                if not response.function_calls:
                    self.logger.debug("Execution loop complete. Returning text.")
                    return response.text
                
                # We have function calls to process
                tool_results = []
                for function_call in response.function_calls:
                    name = function_call.name
                    args = function_call.args
                    self.logger.info(f"Gemini invoking tool: {name}")
                    
                    if tools_registry:
                        try:
                            # args is a dict/mapping natively in genai
                            arg_dict = dict(args) if args else {}
                            result = tools_registry.execute_tool(name, **arg_dict)
                            # the result from execute_tool is a dict representation of ToolResult
                            tool_results.append(
                                types.Part.from_function_response(
                                    name=name,
                                    response={"result": str(result["output"])} if result["success"] else {"error": str(result["error"])}
                                )
                            )
                        except Exception as e:
                            self.logger.error(f"Error executing tool {name}: {e}")
                            tool_results.append(
                                types.Part.from_function_response(
                                    name=name,
                                    response={"error": str(e)}
                                )
                            )
                    else:
                        tool_results.append(
                            types.Part.from_function_response(
                                name=name,
                                response={"error": "Tool registry not explicitly provided."}
                            )
                        )
                
                # Send the tool outputs back to Gemini
                self.logger.info("Sending tool results back to Gemini...")
                response = chat.send_message(tool_results)
                
        except Exception as e:
            self.logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            return f"Error from Gemini explorer: {e}"
