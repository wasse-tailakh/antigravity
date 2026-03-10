import subprocess
from typing import Optional, Any, Dict
from tools.base_tool import BaseTool, ToolResult
from config.logger import get_logger

logger = get_logger("ShellSkill")

class ShellSkill(BaseTool):
    # Hard ceiling on execution time
    MAX_TIMEOUT = 120

    # Commands/patterns that should be blocked for security
    BLOCKED_PATTERNS = [
        # Destructive filesystem operations
        'rm -rf /', 'rm -rf ~', 'rm -rf *', 'rm -rf .', 'rmdir /s',
        'del /s /q', 'rd /s /q',
        # Disk/partition manipulation
        'dd if=', 'mkfs', 'fdisk', 'format c:', 'format d:',
        # Fork bombs and resource exhaustion
        ':(){ :|:& };:', '%0|%0',
        # System shutdown/reboot
        'shutdown', 'reboot', 'init 0', 'init 6', 'halt', 'poweroff',
        # User/permission manipulation
        'chmod 777', 'chown root', 'useradd', 'userdel', 'passwd',
        'net user', 'net localgroup',
        # Network exfiltration
        'curl', 'wget', 'nc ', 'netcat', 'ncat',
        # Registry / system config
        'reg delete', 'reg add', 'regedit',
        # Crypto/ransomware patterns
        'cipher /w', 'gpg --encrypt',
        # Package managers (prevent installing arbitrary packages)
        'pip install', 'npm install', 'apt install', 'yum install',
        'choco install', 'winget install',
    ]
    
    # Dangerous shell metacharacters that enable chaining/injection
    BLOCKED_METACHARACTERS = ['&&', '||', ';', '`', '$(',  '|']

    def __init__(self):
        self._name = "shell_skill"
        
    @property
    def name(self) -> str:
        return self._name
        
    @property
    def description(self) -> str:
        return "Executes shell commands safely within strict security boundaries. Blocks destructive and network commands."
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute."
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30, max 120)."
                }
            },
            "required": ["command"]
        }

    def _is_safe_command(self, command: str) -> bool:
        command_lower = command.lower().strip()
        
        # Check blocked patterns
        for blocked in self.BLOCKED_PATTERNS:
            if blocked in command_lower:
                logger.warning(f"Blocked pattern matched: '{blocked}' in command")
                return False
        
        # Check for shell injection metacharacters
        for meta in self.BLOCKED_METACHARACTERS:
            if meta in command:
                logger.warning(f"Blocked metacharacter '{meta}' detected in command")
                return False
                
        return True

    def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command")
        cwd = kwargs.get("cwd")
        timeout = min(kwargs.get("timeout", 30), self.MAX_TIMEOUT)

        if not command:
            return ToolResult(success=False, output=None, error="Command is required.")

        # Safety check
        if not self._is_safe_command(command):
            logger.warning(f"Security violation blocked: Dangerous command prevented: {command}")
            return ToolResult(success=False, output=None, error=f"Security violation: Command blocked for safety reasons.")

        try:
            logger.info(f"Executing command: {command}")
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            output = result.stdout.strip()
            return ToolResult(success=True, output=output if output else "Command executed successfully (no output)")

        except subprocess.TimeoutExpired as e:
            return ToolResult(success=False, output=None, error=f"Command timed out after {timeout} seconds")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else "No error output"
            return ToolResult(success=False, output=e.stdout, error=f"Command failed (Code {e.returncode}): {stderr}")
        except Exception as e:
            logger.error(f"Unexpected error executing command: {str(e)}", exc_info=True)
            return ToolResult(success=False, output=None, error=f"Error executing command: {str(e)}")
