"""Native OS folder-picker dialog.

Flet's ft.FilePicker control renders as "Unknown control: FilePicker" on this
project's Flet 0.85.3 macOS desktop client regardless of when/how it's added
to the page -- a known, still-unresolved upstream bug (see e.g.
flet-dev/flet#6422 and #6040).

tkinter was tried as a stdlib replacement, but its Tk()/askdirectory() must
run on the main thread on macOS (an AppKit requirement); Flet's own event
loop already owns that thread, and calling it from a worker thread crashes
the whole process with an uncaught NSInternalInconsistencyException. Instead
this shells out to each OS's native folder-picker as a *separate process*,
which has no thread-affinity constraint and is safe to await from a worker
thread via `asyncio.to_thread`.
"""

import subprocess
import sys
from typing import Optional


def choose_directory(title: str, initial_directory: str = "") -> Optional[str]:
    """Block until the user picks a folder or cancels; return the path or None."""
    if sys.platform == "darwin":
        return _choose_directory_macos(title, initial_directory)
    if sys.platform == "win32":
        return _choose_directory_windows(title, initial_directory)
    return _choose_directory_linux(title, initial_directory)


def _choose_directory_macos(title: str, initial_directory: str) -> Optional[str]:
    script = f'POSIX path of (choose folder with prompt {_applescript_quote(title)}'
    if initial_directory:
        script += f' default location (POSIX file {_applescript_quote(initial_directory)})'
    script += ")"
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=600
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None  # user cancelled, or the dialog failed
    return result.stdout.strip() or None


def _applescript_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _choose_directory_windows(title: str, initial_directory: str) -> Optional[str]:
    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = {_powershell_quote(title)}
if ({_powershell_quote(initial_directory)} -ne "") {{
    $dialog.SelectedPath = {_powershell_quote(initial_directory)}
}}
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    Write-Output $dialog.SelectedPath
}}
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except Exception:
        return None
    chosen = result.stdout.strip()
    return chosen or None


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _choose_directory_linux(title: str, initial_directory: str) -> Optional[str]:
    args = ["zenity", "--file-selection", "--directory", f"--title={title}"]
    if initial_directory:
        args.append(f"--filename={initial_directory}/")
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=600)
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None
