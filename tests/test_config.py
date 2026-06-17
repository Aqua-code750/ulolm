import sys
import unittest
import tempfile
import json
from pathlib import Path

# Add local 'src' directory to python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ulolm.config import Config

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_config(self):
        cfg = Config()
        self.assertEqual(cfg.active_model, "UloLMBase")
        self.assertEqual(cfg.backend, "mock")

    def test_save_and_load(self):
        cfg = Config()
        cfg.active_model = "UloLMPro"
        cfg.backend = "openai"
        cfg.save(self.config_path)

        loaded = Config()
        loaded.load(self.config_path)
        self.assertEqual(loaded.active_model, "UloLMPro")
        self.assertEqual(loaded.backend, "openai")

if __name__ == "__main__":
    unittest.main()
