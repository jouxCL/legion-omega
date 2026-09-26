import unittest
import os
import sys
import json
import asyncio

# Add Legion_Omega_V0.4_CREWAI to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.memory_manager import MemoryManager
from crew.tools.flutter_tools import write_dart_file, _run
from crew.runtime import get_runtime


class TestCrewToolsAndMemory(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "tmp_test_project")
        os.makedirs(self.test_dir, exist_ok=True)
        self.memory_file = os.path.join(self.test_dir, "test_memory.json")
        self.memory = MemoryManager(memory_file=self.memory_file)

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_memory_token_usage_and_budget(self):
        self.memory.reset()
        self.memory.update_memory("project.budget_usd", 1.0)
        self.memory.update_memory("project.budget_remaining_usd", 1.0)

        self.memory.log_token_usage("planner", 1000, 500)
        rem = self.memory.get_remaining_budget()
        self.assertLess(rem, 1.0)
        self.assertGreater(rem, 0.0)

    def test_write_dart_file_path_normalization(self):
        runtime = get_runtime()
        from crew.state import ProjectState
        class DummyFlow:
            def __init__(self, path):
                self.state = ProjectState()
                self.state.project_path = path

        runtime.flow = DummyFlow(self.test_dir)
        runtime.memory = self.memory

        # Pass relative path without 'lib/'
        res_raw = write_dart_file._run("features/home/home_page.dart", "// test content")
        res = json.loads(res_raw)
        self.assertTrue(res["success"], res)
        written_path = res["path"]

        # Ensure file was created under lib/
        expected_substr = os.path.join("lib", "features", "home", "home_page.dart")
        self.assertIn(expected_substr, written_path)
        self.assertTrue(os.path.exists(written_path))

    def test_run_helper_event_loop_detection(self):
        async def dummy_coro():
            await asyncio.sleep(0.01)
            return 42

        # Executing _run inside an active event loop
        async def test_inside_loop():
            val = _run(dummy_coro())
            return val

        result = asyncio.run(test_inside_loop())
        self.assertEqual(result, 42)


if __name__ == "__main__":
    unittest.main()
