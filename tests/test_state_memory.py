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

from crew.state import ProjectPlan, FeaturePlan, ProjectState, _to_name_list
from crew.flow import _parse_plan_json
from memory.memory_manager import MemoryManager


class TestStateAndMemory(unittest.TestCase):

    def test_parse_plan_json_clean(self):
        raw = '{"app_name": "test_app", "app_display_name": "Test App", "features": []}'
        data = _parse_plan_json(raw)
        self.assertEqual(data["app_name"], "test_app")

    def test_parse_plan_json_markdown(self):
        raw = 'Here is the plan:\n```json\n{"app_name": "test_app", "app_display_name": "Test App", "features": []}\n```'
        data = _parse_plan_json(raw)
        self.assertEqual(data["app_name"], "test_app")

    def test_to_name_list_coercion(self):
        mixed = ["entity1", {"name": "entity2"}, {"id": "entity3"}]
        res = _to_name_list(mixed)
        self.assertEqual(res, ["entity1", "entity2", "entity3"])

    def test_memory_manager_basic(self):
        temp_dir = tempfile.mkdtemp()
        mem_file = os.path.join(temp_dir, "test_mem.json")
        try:
            mm = MemoryManager(mem_file)
            data = mm.get_memory()
            self.assertEqual(data["project"]["status"], "idle")

            mm.update_memory("project.status", "active")
            self.assertEqual(mm.get_memory()["project"]["status"], "active")

            mm.log_token_usage("planner", 100, 50)
            self.assertGreater(mm.get_memory()["token_usage"]["planner"]["cost_usd"], 0)
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
