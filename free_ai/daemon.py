"""
OpenCode Daemon Supervisor
Ensures the background OpenCode engine (http://127.0.0.1:4096) is alive,
auto-launching it silently via Windows WinGet location if not already running.
"""

from __future__ import annotations
import os
from pathlib import Path
import subprocess
import time
from typing import Optional
import httpx


DEFAULT_DAEMON_URL = "http://127.0.0.1:4096"


def find_opencode_binary() -> Optional[str]:
    """Locates opencode.exe in WinGet directory or system PATH."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_pattern = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_pattern.exists():
            for p in winget_pattern.glob("SST.opencode*"):
                exe = p / "opencode.exe"
                if exe.exists():
                    return str(exe)

    # Check PATH
    import shutil
    path_exe = shutil.which("opencode")
    if path_exe:
        return path_exe

    return None


def is_daemon_alive(base_url: str = DEFAULT_DAEMON_URL, timeout: float = 1.5) -> bool:
    """Checks if the local OpenCode server is responding to health checks."""
    try:
        with httpx.Client(timeout=timeout) as client:
            res = client.get(f"{base_url.rstrip('/')}/global/health")
            return res.status_code == 200
    except Exception:
        return False


def ensure_daemon_running(
    base_url: str = DEFAULT_DAEMON_URL,
    max_wait_seconds: float = 12.0,
    port: int = 4096,
) -> bool:
    """
    Validates daemon health. If offline, attempts to auto-spawn opencode serve.
    Returns True if daemon is ready, False otherwise.
    """
    if is_daemon_alive(base_url):
        return True

    exe = find_opencode_binary()
    if not exe:
        return False

    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

    try:
        subprocess.Popen(
            [exe, "serve", "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
    except Exception:
        return False

    # Poll until ready
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        time.sleep(0.6)
        if is_daemon_alive(base_url):
            return True

    return False
