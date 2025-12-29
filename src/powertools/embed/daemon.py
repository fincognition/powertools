"""
Launchd daemon management for powertools-embed.

Handles installing, starting, stopping, and checking status of the embedding
server daemon on macOS.
"""

import plistlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

# Daemon identifiers
DAEMON_LABEL = "ai.powertools.embed"
PLIST_FILENAME = f"{DAEMON_LABEL}.plist"

# Paths
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / PLIST_FILENAME

# Default config
DEFAULT_PORT = 8384
DEFAULT_HOST = "127.0.0.1"


def get_powertools_embed_path() -> str | None:
    """Find the powertools-embed executable."""
    # Try to find in PATH
    result = shutil.which("powertools-embed")
    if result:
        return result

    # Try common locations
    possible_paths = [
        Path.home() / ".local" / "bin" / "powertools-embed",
        Path("/usr/local/bin/powertools-embed"),
        Path("/opt/homebrew/bin/powertools-embed"),
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    return None


def generate_plist(
    executable_path: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    model: str | None = None,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate launchd plist dictionary."""

    # Build program arguments
    args = [
        executable_path,
        "--host",
        host,
        "--port",
        str(port),
        "--preload",  # Preload model on startup for faster first request
    ]

    if model:
        args.extend(["--model", model])

    # Log directory
    if log_dir is None:
        log_dir = Path.home() / ".powertools" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = str(log_dir / "embed-stdout.log")
    stderr_log = str(log_dir / "embed-stderr.log")

    plist = {
        "Label": DAEMON_LABEL,
        "ProgramArguments": args,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": stdout_log,
        "StandardErrorPath": stderr_log,
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin",
        },
        # Restart on crash, but not too aggressively
        "ThrottleInterval": 10,
    }

    return plist


def is_installed() -> bool:
    """Check if the daemon plist is installed."""
    return PLIST_PATH.exists()


def is_running() -> bool:
    """Check if the daemon is currently running."""
    try:
        result = subprocess.run(
            ["launchctl", "list", DAEMON_LABEL],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_status() -> dict[str, Any]:
    """Get detailed daemon status."""
    status: dict[str, Any] = {
        "installed": is_installed(),
        "running": False,
        "pid": None,
        "exit_code": None,
        "plist_path": str(PLIST_PATH) if is_installed() else None,
    }

    if not status["installed"]:
        return status

    try:
        result = subprocess.run(
            ["launchctl", "list", DAEMON_LABEL],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            output = result.stdout

            # Parse the plist-like output from launchctl
            # Look for "PID" = <number>;
            import re

            pid_match = re.search(r'"PID"\s*=\s*(\d+)', output)
            if pid_match:
                status["pid"] = int(pid_match.group(1))
                status["running"] = True

            exit_match = re.search(r'"LastExitStatus"\s*=\s*(\d+)', output)
            if exit_match:
                status["exit_code"] = int(exit_match.group(1))

    except Exception:
        pass

    return status


def install(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    model: str | None = None,
) -> tuple[bool, str]:
    """
    Install the daemon plist.

    Returns (success, message).
    """
    # Find executable
    executable = get_powertools_embed_path()
    if not executable:
        return False, (
            "Could not find powertools-embed executable. "
            "Make sure powertools is installed with MLX support: "
            "pip install 'powertools[mlx]'"
        )

    # Generate plist
    plist = generate_plist(
        executable_path=executable,
        host=host,
        port=port,
        model=model,
    )

    # Ensure directory exists
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write plist
    try:
        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(plist, f)
    except Exception as e:
        return False, f"Failed to write plist: {e}"

    return True, f"Installed daemon plist at {PLIST_PATH}"


def uninstall() -> tuple[bool, str]:
    """
    Uninstall the daemon plist.

    Returns (success, message).
    """
    # Stop first if running
    if is_running():
        stop()

    # Remove plist
    if PLIST_PATH.exists():
        try:
            PLIST_PATH.unlink()
            return True, f"Removed daemon plist from {PLIST_PATH}"
        except Exception as e:
            return False, f"Failed to remove plist: {e}"
    else:
        return True, "Daemon plist was not installed"


def start() -> tuple[bool, str]:
    """
    Start the daemon.

    Returns (success, message).
    """
    if not is_installed():
        return False, "Daemon is not installed. Run 'pt embed install' first."

    if is_running():
        return True, "Daemon is already running"

    try:
        result = subprocess.run(
            ["launchctl", "load", str(PLIST_PATH)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return True, "Daemon started"
        else:
            return False, f"Failed to start daemon: {result.stderr}"
    except Exception as e:
        return False, f"Failed to start daemon: {e}"


def stop() -> tuple[bool, str]:
    """
    Stop the daemon.

    Returns (success, message).
    """
    if not is_installed():
        return False, "Daemon is not installed"

    if not is_running():
        return True, "Daemon is not running"

    try:
        result = subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return True, "Daemon stopped"
        else:
            return False, f"Failed to stop daemon: {result.stderr}"
    except Exception as e:
        return False, f"Failed to stop daemon: {e}"


def restart() -> tuple[bool, str]:
    """
    Restart the daemon.

    Returns (success, message).
    """
    if is_running():
        success, msg = stop()
        if not success:
            return False, f"Failed to stop: {msg}"

    return start()


def get_logs(lines: int = 50) -> tuple[str, str]:
    """
    Get recent daemon logs.

    Returns (stdout_logs, stderr_logs).
    """
    log_dir = Path.home() / ".powertools" / "logs"
    stdout_log = log_dir / "embed-stdout.log"
    stderr_log = log_dir / "embed-stderr.log"

    stdout_content = ""
    stderr_content = ""

    if stdout_log.exists():
        try:
            with open(stdout_log) as f:
                all_lines = f.readlines()
                stdout_content = "".join(all_lines[-lines:])
        except Exception:
            pass

    if stderr_log.exists():
        try:
            with open(stderr_log) as f:
                all_lines = f.readlines()
                stderr_content = "".join(all_lines[-lines:])
        except Exception:
            pass

    return stdout_content, stderr_content
