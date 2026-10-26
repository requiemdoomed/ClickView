"""Best-effort foreground process detection; unknown means do not capture."""

import os
import sys
import subprocess

DEFAULT_EXCLUSIONS = ("1password", "bitwarden", "keepass", "lastpass")


def foreground_app():
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            import psutil

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetForegroundWindow.restype = wintypes.HWND
            user32.GetWindowThreadProcessId.argtypes = [
                wintypes.HWND,
                ctypes.POINTER(wintypes.DWORD),
            ]
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(
                user32.GetForegroundWindow(), ctypes.byref(pid)
            )
            return psutil.Process(pid.value).name()
        if sys.platform == "darwin":
            return (
                subprocess.check_output(
                    [
                        "osascript",
                        "-e",
                        'tell application "System Events" to get name of first application process whose frontmost is true',
                    ],
                    timeout=1,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            return None
        return (
            subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowclassname"],
                timeout=1,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


def allowed(app, exclusions=DEFAULT_EXCLUSIONS, paused=False):
    return bool(
        not paused
        and app
        and not any(
            x.strip().casefold() in app.casefold() for x in exclusions if x.strip()
        )
    )


# Narrow patterns avoid treating ordinary numbers or code as credentials.
import re

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
)


def looks_sensitive(text):
    """Recognizing a few common key formats, not every possible secret."""
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)
