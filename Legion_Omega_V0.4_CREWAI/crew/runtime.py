"""Process-wide runtime registry for CrewAI tools.

CrewAI tools are invoked by the LLM, so they cannot receive arbitrary Python
objects through arguments. This module exposes a single `Runtime` instance
that tools reach via `get_runtime()` to access the live Flow state, memory,
and a user-notification callback (wired by `tg_bot`).
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from memory.memory_manager import MemoryManager
    from crew.state import ProjectState
    from crew.flow import LegionOmegaFlow

NotifyFn = Callable[[str], Awaitable[None]]


@dataclass
class Runtime:
    memory: Optional["MemoryManager"] = None
    flow: Optional["LegionOmegaFlow"] = None
    notify: Optional[NotifyFn] = None
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    # Main event loop stored by the Telegram bot at startup so tools
    # running in CrewAI worker threads can schedule coroutines safely.
    main_loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def state(self) -> Optional["ProjectState"]:
        return self.flow.state if self.flow is not None else None

    def schedule(self, coro) -> None:
        """Schedule a coroutine on the main event loop from any thread."""
        if self.main_loop is None or self.main_loop.is_closed():
            raise RuntimeError("main_loop not set — bot not started yet")
        asyncio.run_coroutine_threadsafe(coro, self.main_loop)

    def publish_event(self, evt: dict) -> None:
        try:
            self.event_queue.put_nowait(evt)
        except asyncio.QueueFull:
            pass


_runtime = Runtime()


def get_runtime() -> Runtime:
    return _runtime
