import subprocess

class ShellSkill:
    def __init__(self):
        self.name = "shell_skill"
        
    def execute_command(self, command: str, cwd: str = None) -> str:
        """Executes a shell command safely"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Command failed with exit code {e.returncode}\nError: {e.stderr}"
        except Exception as e:
            return f"Error executing command: {str(e)}"
