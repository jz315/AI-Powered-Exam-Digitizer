import io
import os
import sys

def _fix():
    if getattr(sys, "frozen", False):
        if sys.stdout is None:
            sys.stdout = io.TextIOWrapper(open(os.devnull, "wb"), encoding="utf-8", write_through=True)
        if sys.stderr is None:
            sys.stderr = io.TextIOWrapper(open(os.devnull, "wb"), encoding="utf-8", write_through=True)

_fix()
