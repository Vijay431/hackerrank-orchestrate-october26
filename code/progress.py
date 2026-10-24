"""Stderr progress for long stages: a live bar on a terminal, 10% line steps otherwise."""
import sys
import time


class Progress:
    def __init__(self, label: str, total: int):
        self.label, self.total, self.done = label, max(total, 1), 0
        self.tty = sys.stderr.isatty()
        self.start = time.monotonic()
        self.last_step = -1
        self._show()

    def update(self, n: int = 1):
        self.done += n
        self._show()

    def close(self):
        self.done = self.total
        self._show(final=True)

    def _show(self, final: bool = False):
        pct = 100 * self.done // self.total
        line = f"{self.label}: {self.done}/{self.total} {pct}% ({time.monotonic() - self.start:.0f}s)"
        if self.tty:
            filled = 20 * self.done // self.total
            sys.stderr.write(f"\r{self.label} [{'#' * filled}{'.' * (20 - filled)}] "
                             f"{self.done}/{self.total} {pct}% ({time.monotonic() - self.start:.0f}s)"
                             + ("\n" if final else ""))
            sys.stderr.flush()
        elif pct // 10 != self.last_step:
            self.last_step = pct // 10
            print(line, file=sys.stderr, flush=True)
