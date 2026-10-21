import subprocess
import re
from typing import Dict, Any, Tuple

class PowerShellTool:
    """
    Agentic PowerShell Executor with intelligent safety analysis.
    Executes safe queries automatically; flags destructive commands for user confirmation.
    """

    # Commands that alter or delete system state
    DANGEROUS_PATTERNS = [
        # File/Directory deletion & overwrites
        r"\b(remove-item|del|rmdir|rd|ri|rm|erase)\b",
        r"\b(clear-content|clear-recyclebin|set-content|out-file)\b",
        # Process termination
        r"\b(stop-process|kill|spps|taskkill|tskill)\b",
        # Machine state & reboot/shutdown
        r"\b(stop-computer|restart-computer|shutdown)\b",
        # Volume/Disk formatting & shadow copies
        r"\b(format-volume|format|format-disk|diskpart)\b",
        r"\b(vssadmin|bcdedit|wbadmin)\b",
        # Execution policy, user/group modification, permissions
        r"\b(set-executionpolicy)\b",
        r"\b(net\s+user|net\s+localgroup)\b",
        r"\b(icacls|takeown|cipher)\b",
        # Registry deletion
        r"\b(reg\s+delete|remove-itemproperty)\b",
        # Dynamic evaluation, download cradles & encoded commands
        r"\b(invoke-expression|iex|invoke-command)\b",
        r"\b(downloadstring|downloadfile|frombase64string)\b",
        r"(?:-enc|-encodedcommand)\b",
        r"\[system\.convert\]::frombase64string"
    ]

    def __init__(self, safe_mode: bool = True, timeout: int = 30):
        self.safe_mode = safe_mode
        self.timeout = timeout

    def is_safe(self, command: str) -> Tuple[bool, str]:
        """
        Analyzes a PowerShell command to verify if it's safe to run automatically.
        Returns (is_safe, reason).
        """
        if not self.safe_mode:
            return True, "Safe mode disabled."

        # Strip PowerShell escape backticks to prevent backtick-obfuscation bypasses (e.g. r`e`m`o`v`e)
        cleaned_cmd = command.replace("`", "").lower()

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cleaned_cmd, re.IGNORECASE):
                return False, f"Potentially destructive operation detected matching '{pattern}'."

        return True, "Command verified as safe."

    def execute(self, command: str, force: bool = False) -> Dict[str, Any]:
        """
        Executes the PowerShell command and returns output, errors, and return code.
        """
        safe, reason = self.is_safe(command)
        if not safe and not force:
            return {
                "success": False,
                "needs_confirmation": True,
                "command": command,
                "reason": reason,
                "output": f"Security Warning: Command requires user confirmation before execution ({reason})."
            }

        try:
            # Run PowerShell with NoProfile and UTF-8 encoding
            process = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout, stderr = process.communicate(timeout=self.timeout)
            exit_code = process.returncode

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "command": command,
                "output": stdout.strip() if stdout else "",
                "error": stderr.strip() if stderr else ""
            }
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                "success": False,
                "exit_code": -1,
                "command": command,
                "output": "",
                "error": f"Execution timed out after {self.timeout} seconds."
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "command": command,
                "output": "",
                "error": str(e)
            }
