import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path

# Add local 'src' directory to python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ulolm.memory import ProjectMemory

class TestProjectMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = ProjectMemory(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization(self):
        self.memory.initialize()
        self.assertTrue(self.memory.db_path.exists())
        self.assertTrue(self.memory.state_path.exists())
        
        # Verify schema table names
        conn = sqlite3.connect(self.memory.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        self.assertIn("files", tables)
        self.assertIn("symbols", tables)

    def test_scan_and_sync_with_python_symbols(self):
        self.memory.initialize()
        
        # Create a sample python file to index
        src_dir = Path(self.temp_dir.name) / "src"
        src_dir.mkdir()
        code_file = src_dir / "player.py"
        
        code_content = """
class PlayerCharacter:
    \"\"\"Represents the main game protagonist.\"\"\"
    def __init__(self):
        pass

def calculate_score(points):
    \"\"\"Helper to track points.\"\"\"
    return points * 10
"""
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code_content)
            
        # Run scan
        modified = self.memory.scan_and_sync()
        self.assertIn(str(Path("src/player.py")), modified)
        
        # Check SQLite entries
        conn = sqlite3.connect(self.memory.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT filepath, symbol_name, symbol_type FROM symbols")
        symbols = cursor.fetchall()
        conn.close()
        
        self.assertEqual(len(symbols), 3)
        # Verify symbol name and class detection
        self.assertIn((str(Path("src/player.py")), "PlayerCharacter", "class"), symbols)
        self.assertIn((str(Path("src/player.py")), "__init__", "function"), symbols)
        self.assertIn((str(Path("src/player.py")), "calculate_score", "function"), symbols)

if __name__ == "__main__":
    unittest.main()
