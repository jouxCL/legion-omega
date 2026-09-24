import unittest
import json
import tempfile
import os
import shutil
from pathlib import Path

import sys
ROOT_V04 = Path(__file__).resolve().parent.parent / "Legion_Omega_V0.4_CREWAI"
if str(ROOT_V04) not in sys.path:
    sys.path.insert(0, str(ROOT_V04))

from crew.runtime import get_runtime
from crew.tools.memory_tools import get_project_status, get_last_events, list_artifacts
from crew.tools.comms_tools import start_project, cancel_project
from crew.flow import LegionOmegaFlow


class TestTools(unittest.TestCase):

    def setUp(self):
        self.runtime = get_runtime()
        self.runtime.flow = LegionOmegaFlow()

    def test_get_project_status_tool(self):
        # Test tool invocation via .func or direct call
        res_str = get_project_status.func() if hasattr(get_project_status, "func") else get_project_status()
        data = json.loads(res_str)
        self.assertEqual(data["phase"], "idle")

    def test_cancel_project_tool(self):
        res_str = cancel_project.func() if hasattr(cancel_project, "func") else cancel_project()
        data = json.loads(res_str)
        self.assertTrue(data["success"])
        self.assertEqual(self.runtime.state.phase, "failed")


if __name__ == "__main__":
    unittest.main()
