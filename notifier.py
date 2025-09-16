import threading
import time
import tkinter as tk
from typing import Callable, Optional
from storage import log_activity, log_lookfar
from config import LOOK_FAR_UNCLOSEABLE_S


class _BaseWindow:
    def __init__(self, title: str, w: int, h: int, bg: str, text: str, text_fg: str, uncloseable_seconds: int):
        self.reaction_start = time.time()
        self.root = tk.Tk()
        self.root.title(title)
        self.root.configure(bg=bg)
        self.root.attributes('-topmost', True)
        self.root.geometry(f"{w}x{h}+200+200")
        self.root.protocol("WM_DELETE_WINDOW", self._noop)
        self.closed = False
        self._uncloseable_seconds = max(0, int(uncloseable_seconds))

        lbl = tk.Label(self.root, text=text, bg=bg, fg=text_fg, font=("Arial", 48, "bold"))
        lbl.pack(expand=True, fill=tk.BOTH)

        self.btn = tk.Button(self.root, text="Close", state=tk.DISABLED if self._uncloseable_seconds > 0 else tk.NORMAL,
                             command=self._close)
        self.btn.pack(pady=12)

        self.min_btn = tk.Button(self.root, text="Minimize", command=self._minimize)
        self.min_btn.pack(pady=4)

    def _noop(self):
        pass

    def _close(self):
        if not self.closed:
            self.closed = True
            self.root.destroy()

    def _minimize(self):
        self.root.iconify()

    def reveal(self):
        try:
            self.root.deiconify()
        except Exception:
            pass

    def show(self, minimized: bool = False, reveal_when: Optional[Callable[[], bool]] = None):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

        if minimized:
            # schedule minimize as soon as the loop starts
            def do_min():
                # call from the Tk thread
                try:
                    self.root.after(0, self._minimize)
                except Exception:
                    pass

            threading.Timer(0.05, do_min).start()

        if reveal_when is not None:
            def watcher():
                while True:
                    time.sleep(2)
                    try:
                        if reveal_when():
                            # schedule deiconify on Tk thread
                            try:
                                self.root.after(0, self.reveal)
                            except Exception:
                                pass
                            return
                    except Exception:
                        return

            threading.Thread(target=watcher, daemon=True).start()

        return t

    def _run(self):
        if self._uncloseable_seconds > 0:
            self.root.after(self._uncloseable_seconds * 1000, lambda: self.btn.config(state=tk.NORMAL))
        self.root.mainloop()


class LookFarWindow(_BaseWindow):
    def __init__(self):
        super().__init__(
            title="POPATRZ W DAL",
            w=1024,
            h=720,
            bg="#b00020",  # red
            text="POPATRZ W DAL",
            text_fg="#ffffff",
            uncloseable_seconds=LOOK_FAR_UNCLOSEABLE_S,
        )

    def show_and_log(self, minimized: bool = False, reveal_when=None):
        t = super().show(minimized=minimized, reveal_when=reveal_when)

        def waiter():
            t.join()
            reaction = time.time() - self.reaction_start
            log_lookfar(reaction_seconds=reaction, comment="closed/minimized")

        threading.Thread(target=waiter, daemon=True).start()


class StandUpWindow(_BaseWindow):
    def __init__(self):
        super().__init__(
            title="WSTAŃ OD KOMPUTERA",
            w=640,
            h=360,
            bg="#1565c0",  # blue
            text="WSTAŃ OD KOMPUTERA",
            text_fg="#ffffff",
            uncloseable_seconds=0,  # can be closed immediately
        )

    def show_and_log(self, minimized: bool = False, reveal_when=None):
        t = super().show(minimized=minimized, reveal_when=reveal_when)

        def waiter():
            t.join()
            reaction = time.time() - self.reaction_start
            log_activity("standup_close", details=f"reaction={reaction:.1f}s", work_min=0, break_min=0, absence_min=0)

        threading.Thread(target=waiter, daemon=True).start()
