import unittest
from tools.powershell_tool import PowerShellTool

class TestPowerShellTool(unittest.TestCase):

    def setUp(self):
        self.tool = PowerShellTool(safe_mode=True)

    def test_safe_command_execution(self):
        res = self.tool.execute("Write-Output 'AI_ASSISTANT_OK'")
        self.assertTrue(res["success"])
        self.assertIn("AI_ASSISTANT_OK", res["output"])

    def test_dangerous_command_blocked_in_safe_mode(self):
        res = self.tool.execute("Remove-Item -Recurse -Force C:\\Temp\\dummy")
        self.assertFalse(res["success"])
        self.assertTrue(res.get("needs_confirmation"))
        self.assertIn("Security Warning", res.get("output", ""))

if __name__ == "__main__":
    unittest.main()
