from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The tool's name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A detailed description of what the tool does and when to use it."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema representing the expected input arguments."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Executes the tool with the given arguments."""
        pass
        
    def to_openai_schema(self) -> Dict[str, Any]:
        """Returns the tool schema in OpenAI format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }
    
    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Returns the tool schema in Anthropic format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }
        
    def to_gemini_schema(self) -> Dict[str, Any]:
        """Returns the tool schema in Gemini dict format (mapped to genai.types.FunctionDeclaration)"""
        # Gemini handles the Tool object natively through google.genai.types.Tool,
        # but you generally pass a dictionary or function object.
        # Here we format it conceptually similar for the registry.
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema
        }
