import os
from pathlib import Path
from tools.base_tool import BaseTool, ToolResult
from config.logger import get_logger

logger = get_logger("FileSkill")

class FileSkill(BaseTool):
    def __init__(self, project_root: str):
        self._name = "file_skill"
        self._project_root = Path(project_root).resolve()
        
    @property
    def name(self) -> str:
        return self._name
        
    @property
    def description(self) -> str:
        return "Reads from and writes to files within the project root. Use for any file manipulation tasks."
        
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform: 'read' or 'write'",
                    "enum": ["read", "write"]
                },
                "filepath": {
                    "type": "string",
                    "description": "The relative or absolute path to the file."
                },
                "content": {
                    "type": "string",
                    "description": "The content to write (only required for 'write' action)."
                }
            },
            "required": ["action", "filepath"]
        }
        
    def _is_safe_path(self, filepath: str) -> bool:
        """Ensures the path is within the project root."""
        try:
            target_path = Path(filepath).resolve()
            return self._project_root in target_path.parents or target_path == self._project_root
        except Exception:
            return False

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        filepath = kwargs.get("filepath")
        content = kwargs.get("content")
        
        if action not in ["read", "write"]:
             return ToolResult(success=False, output=None, error="Invalid action. Use 'read' or 'write'.")
             
        if not filepath:
             return ToolResult(success=False, output=None, error="Filepath is required.")
             
        # Resolve path relative to project root if it's not absolute
        target_path = Path(filepath)
        if not target_path.is_absolute():
            target_path = self._project_root / target_path
            
        if not self._is_safe_path(str(target_path)):
            logger.warning(f"Security violation blocked: Attempted access outside project root ({self._project_root}) -> {target_path}")
            return ToolResult(success=False, output=None, error=f"Security violation: Access denied to paths outside project root.")

        if action == "read":
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    return ToolResult(success=True, output=f.read())
            except Exception as e:
                return ToolResult(success=False, output=None, error=f"Error reading file {filepath}: {str(e)}")
                
        elif action == "write":
            if content is None:
                 return ToolResult(success=False, output=None, error="Content is required for write action.")
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return ToolResult(success=True, output=f"Successfully wrote to {filepath}")
            except Exception as e:
                return ToolResult(success=False, output=None, error=f"Error writing to file {filepath}: {str(e)}")
