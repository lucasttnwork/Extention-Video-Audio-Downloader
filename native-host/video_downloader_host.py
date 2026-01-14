#!/usr/bin/env python3
"""
Native Messaging Host for Video Downloader Chrome Extension.
Controls the Flask server lifecycle.
"""
import json
import struct
import sys
import subprocess
import os
import signal
import time
from pathlib import Path

# Path to the server
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
SERVER_PATH = PROJECT_DIR / "server" / "app.py"
PID_FILE = SCRIPT_DIR / "server.pid"

def get_message():
    """Read a message from stdin (Chrome extension)."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def send_message(message):
    """Send a message to stdout (Chrome extension)."""
    encoded = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('=I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

def is_server_running():
    """Check if the Flask server is running."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            return True, pid
        except (OSError, ValueError):
            PID_FILE.unlink(missing_ok=True)
    return False, None

def start_server():
    """Start the Flask server."""
    running, pid = is_server_running()
    if running:
        return {"success": True, "message": "Server already running", "pid": pid}

    try:
        # Start server as subprocess
        process = subprocess.Popen(
            [sys.executable, str(SERVER_PATH)],
            cwd=str(PROJECT_DIR / "server"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent
        )

        # Save PID
        PID_FILE.write_text(str(process.pid))

        # Wait briefly to ensure it started
        time.sleep(1)

        # Verify it's running
        if process.poll() is None:
            return {"success": True, "message": "Server started", "pid": process.pid}
        else:
            PID_FILE.unlink(missing_ok=True)
            return {"success": False, "error": "Server failed to start"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def stop_server():
    """Stop the Flask server."""
    running, pid = is_server_running()
    if not running:
        return {"success": True, "message": "Server not running"}

    try:
        os.kill(pid, signal.SIGTERM)

        # Wait for graceful shutdown
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # Force kill if still running
            os.kill(pid, signal.SIGKILL)

        PID_FILE.unlink(missing_ok=True)
        return {"success": True, "message": "Server stopped"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_status():
    """Get server status."""
    running, pid = is_server_running()
    return {
        "success": True,
        "running": running,
        "pid": pid
    }

def main():
    """Main loop to handle messages from the extension."""
    while True:
        message = get_message()
        if message is None:
            break

        action = message.get("action")

        if action == "start":
            response = start_server()
        elif action == "stop":
            response = stop_server()
        elif action == "status":
            response = get_status()
        else:
            response = {"success": False, "error": f"Unknown action: {action}"}

        send_message(response)

if __name__ == "__main__":
    main()
