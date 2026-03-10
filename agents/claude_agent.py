from typing import Any, Dict, List, Optional
from anthropic import Anthropic
from .base_agent import BaseAgent
from config.settings import settings
from tools.tool_registry import ToolRegistry

class ClaudeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Claude Planner",
            capabilities=["planning", "architecture", "code_review"]
        )
        self.model = "claude-3-5-sonnet-20240620"
        try:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        except Exception as e:
            self.logger.warning(f"Failed to initialize Anthropic client: {e}")
            self.client = None

    def run(self, prompt: str, context: Dict[str, Any] = None, tools_registry: ToolRegistry = None) -> str:
        self.logger.debug(f"Input context: {context}")
        if not self.client:
            return "Error: Claude client is not initialized (missing or invalid API key)."
            
        messages = [{"role": "user", "content": prompt}]
        
        system_prompt = "You are Claude, a helpful AI assistant. You can use tools to accomplish tasks."
        if context:
             system_prompt += f"\nContext: {context}"
             
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
        }
        
        if tools_registry:
            kwargs["tools"] = tools_registry.get_anthropic_tools()
            
        try:
            self.logger.info("Starting Claude execution loop...")
            while True:
                kwargs["messages"] = messages
                response = self.client.messages.create(**kwargs)
                
                # Check for tool use
                tool_uses = [block for block in response.content if block.type == 'tool_use']
                
                if not tool_uses:
                    # Final text response
                    text_blocks = [block.text for block in response.content if block.type == 'text']
                    final_response = "\\n".join(text_blocks)
                    self.logger.debug("Execution loop complete. Returning text.")
                    return final_response
                    
                # We need to append the assistant's request so Claude has history of its tool call
                messages.append({"role": "assistant", "content": response.content})
                
                # Process tools
                for tool_use in tool_uses:
                    self.logger.info(f"Claude invoking tool: {tool_use.name}")
                    if tools_registry:
                        result = tools_registry.execute_tool(tool_use.name, **tool_use.input)
                        # Append the tool result
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": str(result["output"]) if result["success"] else str(result["error"]),
                                    "is_error": not result["success"]
                                }
                            ]
                        })
                    else:
                         messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": "Tool registry not provided.",
                                    "is_error": True
                                }
                            ]
                        })
                        
        except Exception as e:
            self.logger.error(f"Error calling Claude API: {e}", exc_info=True)
            return f"Error from Claude planner: {e}"
