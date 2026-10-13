"""Console helpers shared by the command-line interfaces built on the engine."""

from __future__ import annotations

import contextlib
import sys


def ensure_utf8_console() -> None:
    """Force UTF-8 on stdout/stderr so that accented explanations print everywhere.

    Windows consoles default to a legacy code page (cp1252); without this, printing a
    rule such as ``vitesse EST très rapide`` raises ``UnicodeEncodeError``.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):  # exotic / closed streams
                reconfigure(encoding="utf-8", errors="replace")
