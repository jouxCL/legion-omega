import unittest
from pathlib import Path
import sys

ROOT_V04 = Path(__file__).resolve().parent.parent / "Legion_Omega_V0.4_CREWAI"
if str(ROOT_V04) not in sys.path:
    sys.path.insert(0, str(ROOT_V04))

from crew.flow import LegionOmegaFlow


class TestFlowLogic(unittest.TestCase):

    def test_flow_initialization(self):
        flow = LegionOmegaFlow()
        self.assertEqual(flow.state.phase, "idle")

    def test_slugify(self):
        self.assertEqual(LegionOmegaFlow._slugify("My Cool App!!"), "my_cool_app")
        self.assertEqual(LegionOmegaFlow._slugify(""), "legion_app")


if __name__ == "__main__":
    unittest.main()
