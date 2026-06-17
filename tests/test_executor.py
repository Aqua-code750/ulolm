import sys
import unittest
import tempfile
from pathlib import Path

# Add local 'src' directory to python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ulolm.executor import WorkspaceExecutor

class TestWorkspaceExecutor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.executor = WorkspaceExecutor(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_safe_path(self):
        self.assertTrue(self.executor.is_safe_path("src/main.py"))
        self.assertTrue(self.executor.is_safe_path("config.json"))

    def test_unsafe_path_traversal(self):
        # Prevent accessing files above workspace root
        self.assertFalse(self.executor.is_safe_path("../../etc/passwd"))
        self.assertFalse(self.executor.is_safe_path("../secret.txt"))

    def test_execute_write_tool(self):
        tool_call = {
            "name": "write_file",
            "parameters": {
                "path": "src/test_script.py",
                "content": "print('hello')"
            }
        }
        res = self.executor.execute_tool(tool_call)
        self.assertEqual(res.get("status"), "success")
        
        # Verify file actually written
        target_file = Path(self.temp_dir.name) / "src/test_script.py"
        self.assertTrue(target_file.exists())
        with open(target_file, 'r') as f:
            self.assertEqual(f.read(), "print('hello')")

    def test_execute_unsafe_write(self):
        tool_call = {
            "name": "write_file",
            "parameters": {
                "path": "../malicious.txt",
                "content": "exploit"
            }
        }
        res = self.executor.execute_tool(tool_call)
        self.assertEqual(res.get("status"), "error")
        self.assertIn("Security Exception", res.get("message", ""))

if __name__ == "__main__":
    unittest.main()
