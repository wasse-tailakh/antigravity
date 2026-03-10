from git import Repo, exc, InvalidGitRepositoryError
from pathlib import Path
from typing import Optional, Any, Dict
from tools.base_tool import BaseTool, ToolResult
from config.logger import get_logger

logger = get_logger("GitSkill")


class GitSkill(BaseTool):
    def __init__(self):
        self._name = "git_skill"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Performs Git operations like clone, status, commit, and push."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The git action to perform: 'clone', 'status', 'commit_and_push'",
                    "enum": ["clone", "status", "commit_and_push"]
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the repository (or target dir for clone)."
                },
                "url": {
                    "type": "string",
                    "description": "Repository URL (required for 'clone')."
                },
                "message": {
                    "type": "string",
                    "description": "Commit message (required for 'commit_and_push')."
                }
            },
            "required": ["action", "repo_path"]
        }

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        repo_path = kwargs.get("repo_path")
        
        if action not in ["clone", "status", "commit_and_push"]:
            return ToolResult(success=False, output=None, error="Invalid action.")
            
        if not repo_path:
            return ToolResult(success=False, output=None, error="repo_path is required.")

        if action == "clone":
            url = kwargs.get("url")
            if not url:
                return ToolResult(success=False, output=None, error="url is required for cloning.")
            try:
                Path(repo_path).mkdir(parents=True, exist_ok=True)
                Repo.clone_from(url, repo_path)
                return ToolResult(success=True, output=f"Successfully cloned {url} to {repo_path}")
            except Exception as e:
                return ToolResult(success=False, output=None, error=f"Git clone error: {e}")
                
        elif action == "status":
            try:
                repo = Repo(repo_path)
                return ToolResult(success=True, output=repo.git.status())
            except InvalidGitRepositoryError:
                return ToolResult(success=False, output=None, error=f"Not a valid git repository: {repo_path}")
            except Exception as e:
                return ToolResult(success=False, output=None, error=f"Git status error: {e}")
                
        elif action == "commit_and_push":
            message = kwargs.get("message")
            if not message:
                return ToolResult(success=False, output=None, error="message is required for commit_and_push")
            try:
                repo = Repo(repo_path)
                if not repo.is_dirty(untracked_files=True):
                    return ToolResult(success=True, output="No changes to commit.")
                
                repo.git.add('.')
                repo.index.commit(message)
                result_output = f"Successfully committed changes: {message}"
                
                try:
                    origin = repo.remote(name='origin')
                    origin.push()
                    result_output += " and pushed to remote."
                except exc.GitCommandError as e:
                    result_output += f"\nWarning: Failed to push: {e}"
                    
                return ToolResult(success=True, output=result_output)
            except InvalidGitRepositoryError:
                return ToolResult(success=False, output=None, error=f"Not a valid git repository: {repo_path}")
            except Exception as e:
                return ToolResult(success=False, output=None, error=f"Git commit/push error: {e}")

