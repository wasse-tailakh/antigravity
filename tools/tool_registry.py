from typing import Dict, List, Any
from tools.base_tool import BaseTool
from config.logger import get_logger

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = get_logger("ToolRegistry")

    def register(self, tool: BaseTool):
        """Register a new tool"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> BaseTool:
        """Retrieve a tool by name"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found in registry")
        return self.tools[name]
        
    def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a tool by name with the given arguments natively returning ToolResult dict representation."""
        self.logger.info(f"Executing tool '{name}' with args: {kwargs}")
        try:
            tool = self.get_tool(name)
            result = tool.execute(**kwargs)
            
            if result.success:
                self.logger.info(f"Tool '{name}' executed successfully.")
            else:
                 self.logger.warning(f"Tool '{name}' failed: {result.error}")
                 
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Critical error executing tool '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "output": None,
                "error": str(e),
                "metadata": {}
            }

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools in OpenAI format"""
        return [tool.to_openai_schema() for tool in self.tools.values()]
        
    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools in Anthropic format"""
        return [tool.to_anthropic_schema() for tool in self.tools.values()]

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools in Gemini format"""
        return [tool.to_gemini_schema() for tool in self.tools.values()]
