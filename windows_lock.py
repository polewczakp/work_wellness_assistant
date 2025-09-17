from __future__ import annotations

"""Windows session lock/unlock monitor with a clear API and tests in mind.

- On Windows: creates a hidden message-only window, registers for
  WTS session change notifications, and invokes callbacks on lock/unlock.
- On non-Windows: provides a no-op monitor with the same interface.

Design goals: readability, minimal branching, safe cleanup, and testability.
"""

from dataclasses import dataclass
from typing import Callable, Optional
import sys
import threading

Callback = Optional[Callable[[], None]]


@dataclass
class _Callbacks:
    on_lock: Callback = None
    on_unlock: Callback = None


class _NoopMonitor:
    """Cross-platform stub used when not on Windows."""

    def __init__(self, *_: object, **__: object) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False


class WindowsSessionMonitor:
    """Windows implementation. Requires pywin32.

    Use start()/stop() to control the message loop.
    """

    # Win32 constants (mirrored here for testability and clarity)
    WM_WTSSESSION_CHANGE = 0x02B1
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8

    def __init__(self, on_lock: Callback = None, on_unlock: Callback = None) -> None:
        self.cb = _Callbacks(on_lock=on_lock, on_unlock=on_unlock)
        # Imports are deferred for easier testing
        try:
            import win32api  # type: ignore
            import win32con  # type: ignore
            import win32gui  # type: ignore
            import win32ts  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pywin32 is required on Windows") from exc

        self.win32api = win32api  # for module access in tests
        self.win32con = win32con
        self.win32gui = win32gui
        self.win32ts = win32ts

        self._hwnd = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # Public API
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._hwnd:
            # Post WM_DESTROY to trigger unregistration and exit loop
            self.win32gui.PostMessage(self._hwnd, self.win32con.WM_DESTROY, 0, 0)
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    # Internals
    def _create_window(self) -> int:
        WNDCLASS = self.win32gui.WNDCLASS()
        WNDCLASS.hInstance = self.win32api.GetModuleHandle(None)
        WNDCLASS.lpszClassName = "WWS_Session_Wnd"
        WNDCLASS.lpfnWndProc = self._wnd_proc
        atom = self.win32gui.RegisterClass(WNDCLASS)
        hwnd = self.win32gui.CreateWindow(
            atom,
            "WWS_Session_Wnd",
            0, 0, 0, 0, 0,
            0, 0,
            WNDCLASS.hInstance,
            None,
        )
        return hwnd

    def _run(self) -> None:
        self._hwnd = self._create_window()
        self.win32ts.WTSRegisterSessionNotification(
            self._hwnd, self.win32ts.NOTIFY_FOR_THIS_SESSION
        )
        try:
            self.win32gui.PumpMessages()
        finally:
            # Ensure unregistration even on exceptions
            try:
                self.win32ts.WTSUnRegisterSessionNotification(self._hwnd)
            except Exception:  # pragma: no cover
                pass
            self._hwnd = None

    # Window procedure
    def _wnd_proc(self, hwnd, msg, wparam, lparam):  # pragma: no cover - exercised via tests with fakes
        if msg == self.WM_WTSSESSION_CHANGE:
            if wparam == self.WTS_SESSION_LOCK and self.cb.on_lock:
                self.cb.on_lock()
            elif wparam == self.WTS_SESSION_UNLOCK and self.cb.on_unlock:
                self.cb.on_unlock()
        elif msg == self.win32con.WM_DESTROY:
            # Mirror the cleanup path used in stop()
            try:
                self.win32ts.WTSUnRegisterSessionNotification(hwnd)
            finally:
                self.win32gui.PostQuitMessage(0)
        return self.win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


def create_monitor(on_lock: Callback = None, on_unlock: Callback = None):
    """Factory returning a platform-appropriate monitor instance."""
    if sys.platform != "win32":
        return _NoopMonitor()
    return WindowsSessionMonitor(on_lock=on_lock, on_unlock=on_unlock)


def start_windows_session_monitor(on_lock: Callback = None, on_unlock: Callback = None):
    """Backwards-compatible function used by app.py.

    Returns the monitor instance for optional manual control in callers.
    """
    mon = create_monitor(on_lock=on_lock, on_unlock=on_unlock)
    mon.start()
    return mon
