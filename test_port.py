#!/usr/bin/env python3
"""Test script to find process by port."""
import subprocess
import sys

def get_pid_by_port(port=5050):
    """Get the PID of the process using a specific port."""
    try:
        if sys.platform == "win32":
            # On Windows, use netstat to find the process
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True, text=True, check=False
            )
            print("=== NETSTAT OUTPUT ===")
            print(result.stdout)
            print("=== END NETSTAT ===")

            print(f"\n=== Looking for port {port} ===")
            for line in result.stdout.split('\n'):
                if f":{port}" in line:
                    print(f"Found line: {line}")
                    if "LISTENING" in line:
                        parts = line.split()
                        print(f"Parts: {parts}")
                        if parts:
                            pid = int(parts[-1])
                            print(f"Found PID: {pid}")
                            return pid
        else:
            # On Unix, use lsof
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, check=False
            )
            if result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
    except Exception as e:
        print(f"Error: {e}")
    return None

if __name__ == "__main__":
    port = 5050
    print(f"Searching for process on port {port}...")
    pid = get_pid_by_port(port)
    if pid:
        print(f"\n*** SUCCESS: Found process with PID {pid} on port {port} ***")
    else:
        print(f"\n*** FAILED: No process found on port {port} ***")
