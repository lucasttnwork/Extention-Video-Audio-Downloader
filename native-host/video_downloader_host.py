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
import logging

# Path to the server
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
SERVER_PATH = PROJECT_DIR / "server" / "app.py"
PID_FILE = SCRIPT_DIR / "server.pid"
LOG_FILE = SCRIPT_DIR / "native_host.log"

# Configure logging
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

def get_pid_by_port(port=5050):
    """Get the PID of the process using a specific port."""
    logging.debug(f"get_pid_by_port called for port {port}")
    try:
        if sys.platform == "win32":
            # On Windows, use netstat to find the process
            logging.debug("Running netstat...")
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True, text=True, check=False
            )
            logging.debug(f"netstat returncode: {result.returncode}")
            for line in result.stdout.split('\n'):
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    logging.debug(f"Found matching line: {line.strip()}")
                    logging.debug(f"Parts: {parts}")
                    if parts:
                        pid = int(parts[-1])
                        logging.debug(f"Found PID: {pid}")
                        return pid
            logging.debug(f"No process found on port {port}")
        else:
            # On Unix, use lsof
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, check=False
            )
            if result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
    except Exception as e:
        logging.error(f"Error in get_pid_by_port: {e}")
    return None

def kill_process_by_port(port=5050):
    """Kill the process using a specific port."""
    logging.debug(f"kill_process_by_port called for port {port}")
    pid = get_pid_by_port(port)
    logging.debug(f"get_pid_by_port returned: {pid}")
    if pid:
        try:
            if sys.platform == "win32":
                logging.debug(f"Running taskkill for PID {pid}")
                result = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                              capture_output=True, text=True, check=False)
                logging.debug(f"taskkill result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}")
            else:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            logging.debug(f"Successfully killed process {pid}")
            return True, pid
        except Exception as e:
            logging.error(f"Error killing process: {e}")
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
    logging.info("stop_server called")
    running, pid = is_server_running()
    logging.debug(f"is_server_running returned: running={running}, pid={pid}")

    # If PID file doesn't exist, try to find server by port
    if not running:
        logging.debug("PID file not found, trying to find server by port...")
        killed, port_pid = kill_process_by_port(5050)
        logging.debug(f"kill_process_by_port returned: killed={killed}, port_pid={port_pid}")
        if killed:
            PID_FILE.unlink(missing_ok=True)
            logging.info(f"Server stopped by port, PID: {port_pid}")
            return {"success": True, "message": f"Server stopped (found by port, PID: {port_pid})"}
        logging.info("Server not running (no PID file and no process on port)")
        return {"success": True, "message": "Server not running"}

    try:
        # Platform-specific process termination
        if sys.platform == "win32":
            # On Windows, use taskkill with /T to kill process tree
            # /F = force, /T = tree (kill child processes too)
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                          capture_output=True, check=False)
        else:
            # On Unix, use SIGTERM
            os.kill(pid, signal.SIGTERM)

        # Wait for process to terminate
        for i in range(20):  # Wait up to 10 seconds
            time.sleep(0.5)
            try:
                # Check if process still exists
                if sys.platform == "win32":
                    result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                                          capture_output=True, text=True)
                    if str(pid) not in result.stdout:
                        break  # Process terminated
                else:
                    os.kill(pid, 0)
            except (OSError, subprocess.SubprocessError):
                break  # Process terminated
        else:
            # Force kill if still running after 10 seconds
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                             capture_output=True, check=False)
            else:
                os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)  # Give it a moment to die

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
