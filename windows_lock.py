from __future__ import annotations

import sys
import threading
from typing import Callable, Optional

if sys.platform != "win32":

    def start_windows_session_monitor(  # type: ignore[empty-body]
        *_, **__
    ) -> None:
        return
else:
    import win32api
    import win32con
    import win32gui
    import win32ts

    WM_WTSSESSION_CHANGE = 0x02B1
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8

    class _SessionWindow:
        def __init__(
            self,
            on_lock: Optional[Callable[[], None]] = None,
            on_unlock: Optional[Callable[[], None]] = None,
        ) -> None:
            self.on_lock = on_lock
            self.on_unlock = on_unlock
            self.hinst = win32api.GetModuleHandle(None)
            wndclass = win32gui.WNDCLASS()
            wndclass.hInstance = self.hinst
            wndclass.lpszClassName = "WWS_Session_Wnd"
            wndclass.lpfnWndProc = self._wndproc
            self.class_atom = win32gui.RegisterClass(wndclass)
            self.hwnd = win32gui.CreateWindow(
                self.class_atom,
                "WWS_Session_Wnd",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                self.hinst,
                None,
            )
            win32ts.WTSRegisterSessionNotification(
                self.hwnd, win32ts.NOTIFY_FOR_THIS_SESSION
            )

        def _wndproc(self, hwnd, msg, wparam, lparam):
            if msg == WM_WTSSESSION_CHANGE:
                if wparam == WTS_SESSION_LOCK and self.on_lock:
                    self.on_lock()
                elif wparam == WTS_SESSION_UNLOCK and self.on_unlock:
                    self.on_unlock()
            elif msg == win32con.WM_DESTROY:
                win32ts.WTSUnRegisterSessionNotification(hwnd)
                win32gui.PostQuitMessage(0)
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

        def loop(self) -> None:
            win32gui.PumpMessages()

    def start_windows_session_monitor(
        on_lock: Optional[Callable[[], None]] = None,
        on_unlock: Optional[Callable[[], None]] = None,
    ) -> None:
        def _run() -> None:
            wnd = _SessionWindow(on_lock=on_lock, on_unlock=on_unlock)
            wnd.loop()

        threading.Thread(target=_run, daemon=True).start()
