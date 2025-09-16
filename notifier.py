from __future__ import annotations

import threading
import time
import tkinter as tk
from typing import Callable, Optional

from config import LOOK_FAR_UNCLOSEABLE_S
from storage import log_activity, log_lookfar


class _BaseWindow:
    def __init__(
        self,
        title: str,
        w: int,
        h: int,
        bg: str,
        text: str,
        text_fg: str,
        uncloseable_seconds: int,
    ) -> None:
        self.reaction_start = time.time()
        self.closed = False
        self._uncloseable_seconds = max(0, int(uncloseable_seconds))
        self.root = tk.Tk()
        self._init_root(title, w, h, bg)
        self._init_body(text, bg, text_fg)

    def _init_root(self, title: str, w: int, h: int, bg: str) -> None:
        self.root.title(title)
        self.root.configure(bg=bg)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{w}x{h}+200+200")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

    def _init_body(self, text: str, bg: str, text_fg: str) -> None:
        tk.Label(
            self.root, text=text, bg=bg, fg=text_fg, font=("Arial", 48, "bold")
        ).pack(expand=True, fill=tk.BOTH)
        state = tk.DISABLED if self._uncloseable_seconds > 0 else tk.NORMAL
        self.btn = tk.Button(self.root, text="Close", state=state, command=self._close)
        self.btn.pack(pady=12)
        tk.Button(self.root, text="Minimize", command=self._minimize).pack(pady=4)

    def _close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.root.destroy()

    def _minimize(self) -> None:
        self.root.iconify()

    def reveal(self) -> None:
        self.root.deiconify()

    def _delayed_enable(self) -> None:
        if self._uncloseable_seconds <= 0:
            return
        self.root.after(
            self._uncloseable_seconds * 1000, lambda: self.btn.config(state=tk.NORMAL)
        )

    def show(
        self, minimized: bool = False, reveal_when: Optional[Callable[[], bool]] = None
    ) -> threading.Thread:
        t = threading.Thread(target=self._run_mainloop, daemon=True)
        t.start()
        if minimized:
            threading.Timer(0.05, self._minimize).start()
        if reveal_when is not None:
            threading.Thread(
                target=self._watch_and_reveal, args=(reveal_when,), daemon=True
            ).start()
        return t

    def _watch_and_reveal(self, reveal_when: Callable[[], bool]) -> None:
        while True:
            time.sleep(2)
            if reveal_when():
                self.root.after(0, self.reveal)
                return

    def _run_mainloop(self) -> None:
        self._delayed_enable()
        self.root.mainloop()


class LookFarWindow(_BaseWindow):
    def __init__(self) -> None:
        super().__init__(
            title="POPATRZ W DAL",
            w=1024,
            h=720,
            bg="#b00020",  # red
            text="POPATRZ W DAL",
            text_fg="#ffffff",
            uncloseable_seconds=LOOK_FAR_UNCLOSEABLE_S,
        )

    def show_and_log(self, minimized: bool = False, reveal_when=None) -> None:
        t = super().show(minimized=minimized, reveal_when=reveal_when)

        def waiter() -> None:
            t.join()
            reaction = time.time() - self.reaction_start
            log_lookfar(reaction_seconds=reaction, comment="closed/minimized")

        threading.Thread(target=waiter, daemon=True).start()


class StandUpWindow(_BaseWindow):
    def __init__(self) -> None:
        super().__init__(
            title="WSTAŃ OD KOMPUTERA",
            w=640,
            h=360,
            bg="#1565c0",  # blue
            text="WSTAŃ OD KOMPUTERA",
            text_fg="#ffffff",
            uncloseable_seconds=0,  # can be closed immediately
        )

    def show_and_log(self, minimized: bool = False, reveal_when=None) -> None:
        t = super().show(minimized=minimized, reveal_when=reveal_when)

        def waiter() -> None:
            t.join()
            reaction = time.time() - self.reaction_start
            log_activity(
                "standup_close",
                details=f"reaction={reaction:.1f}s",
                work_min=0,
                break_min=0,
                absence_min=0,
            )

        threading.Thread(target=waiter, daemon=True).start()
