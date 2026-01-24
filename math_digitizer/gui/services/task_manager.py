from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional


StatusFn = Callable[[str], None]
LogFn = Callable[[str], None]
ShowCancelFn = Callable[[str], None]
HideCancelFn = Callable[[], None]
CancelHandler = Callable[[], None]


@dataclass
class TaskManager:
    on_show_cancel: ShowCancelFn
    on_hide_cancel: HideCancelFn
    on_status: Optional[StatusFn] = None
    on_log: Optional[LogFn] = None
    _cancel_event: threading.Event = field(default_factory=threading.Event, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _running: bool = field(default=False, init=False)
    _name: str = field(default="", init=False)
    _cancel_handlers: list[CancelHandler] = field(default_factory=list, init=False)

    def start(self, name: str, *, cancel_handlers: list[CancelHandler] | None = None) -> None:
        with self._lock:
            self._running = True
            self._name = name
            self._cancel_event.clear()
            self._cancel_handlers = list(cancel_handlers or [])
        self.on_show_cancel(name)

    def request_cancel(self, reason: str = "user") -> None:
        with self._lock:
            if not self._running:
                return
            self._cancel_event.set()
            handlers = list(self._cancel_handlers)
        for handler in handlers:
            try:
                handler()
            except Exception:
                pass
        if self.on_status:
            self.on_status("⏹ 正在取消任务...")
        if self.on_log:
            self.on_log(f"[info] Task cancellation requested ({reason})")

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def finish(self) -> None:
        with self._lock:
            self._running = False
            self._name = ""
            self._cancel_handlers = []
        self.on_hide_cancel()

    def is_running(self) -> bool:
        return self._running

    def name(self) -> str:
        return self._name
