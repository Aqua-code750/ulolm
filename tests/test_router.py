import sys
import unittest
from pathlib import Path

# Add local 'src' directory to python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ulolm.router import ExpertRouter

class TestExpertRouter(unittest.TestCase):
    def setUp(self):
        self.router = ExpertRouter()

    def test_routing_game_development(self):
        profile = self.router.route("create a pygame platformer shooter")
        self.assertEqual(profile.name, "Game Development Expert")

    def test_routing_design(self):
        profile = self.router.route("write a css styled frontend layout with neon color palette")
        self.assertEqual(profile.name, "Design Expert")

    def test_routing_math(self):
        profile = self.router.route("calculate the vector rotation for 45 degrees around the Z axis")
        self.assertEqual(profile.name, "Math Expert")

    def test_routing_coding_default(self):
        profile = self.router.route("refactor a bubble sort in python")
        self.assertEqual(profile.name, "Coding Expert")

if __name__ == "__main__":
    unittest.main()
