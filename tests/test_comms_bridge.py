import unittest
import asyncio
from pathlib import Path
import sys

ROOT_V04 = Path(__file__).resolve().parent.parent / "Legion_Omega_V0.4_CREWAI"
if str(ROOT_V04) not in sys.path:
    sys.path.insert(0, str(ROOT_V04))

from crew.runtime import get_runtime
from tg_bot.comms_bridge import event_narrator_loop


class TestCommsBridge(unittest.TestCase):

    def test_event_narrator_messages(self):
        async def _test():
            sent = []
            async def mock_send(msg):
                sent.append(msg)

            rt = get_runtime()
            rt.publish_event({"phase": "init", "app_name": "test_app"})

            task = asyncio.create_task(event_narrator_loop(mock_send))
            await asyncio.sleep(0.1)
            task.cancel()

            self.assertTrue(len(sent) >= 1)
            self.assertIn("test_app", sent[0])

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
