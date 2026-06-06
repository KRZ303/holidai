import os
import sys
import time
import socket
import select
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HELPER_PATH = os.path.join(SCRIPT_DIR, "cdp_helper.js")
DEFAULT_EVAL_TIMEOUT_SECONDS = 60
CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def is_port_open(port=9222):
    """
    Checks if a remote debugging port is already open and listening.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(('127.0.0.1', port))
            return True
        except OSError:
            return False

def ensure_browser(port=9222, profile_dir=None, default_url="https://www.booking.com", login_prompt=None):
    """
    Ensures that a Chrome instance is running with remote debugging port.
    If not, automatically launches Chrome Stable on macOS with an isolated profile.
    """
    if is_port_open(port):
        print(f"Found active Chrome debugger on port {port}.")
    else:
        print(f"No active Chrome debugger found on port {port}. Attempting to launch Google Chrome...")
        if not os.path.exists(CHROME_BINARY):
            print("Error: Google Chrome was not found at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome.", file=sys.stderr)
            print("Install stable Google Chrome or launch it manually with:", file=sys.stderr)
            profile_hint = profile_dir or os.path.join(os.getcwd(), "chrome-profile")
            print(
                f"  {CHROME_BINARY} --remote-debugging-port={port} --user-data-dir={profile_hint} {default_url}",
                file=sys.stderr,
            )
            return False

        if not profile_dir:
            profile_dir = os.path.join(os.getcwd(), "chrome-profile")
        os.makedirs(profile_dir, exist_ok=True)

        cmd = [
            CHROME_BINARY,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            default_url
        ]

        print("Launching Google Chrome...")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for port to open
        for _ in range(20):
            time.sleep(0.5)
            if is_port_open(port):
                print(f"Chrome started and listening on port {port}.")
                break
        else:
            print(f"Error: Timed out waiting for Chrome to listen on port {port}.", file=sys.stderr)
            return False
    
    if login_prompt:
        print("\n" + "=" * 70)
        print(login_prompt)
        print("Confirm Google Chrome is logged in and exactly one Booking.com tab is open.")
        print("Type OK to continue. Any other input exits before navigation.")
        print("=" * 70 + "\n")
        if input("> ").strip() != "OK":
            print("Did not receive OK. Exiting before navigation.")
            return False
        
    return True

def run_chrome_open(url, helper_path=DEFAULT_HELPER_PATH, timeout=40):
    """
    Navigates the active tab to the specified URL.
    """
    try:
        proc = subprocess.run(["node", helper_path, "navigate", url], capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0:
            return True, None
        else:
            return False, proc.stderr.strip()
    except Exception as e:
        return False, str(e)

def run_chrome_eval(script, helper_path=DEFAULT_HELPER_PATH, timeout=DEFAULT_EVAL_TIMEOUT_SECONDS):
    """
    Evaluates JavaScript in the active tab and returns the result.
    """
    try:
        proc = subprocess.Popen(["node", helper_path, "eval"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(input=script, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            timeout_message = f"Timed out after {timeout} seconds while evaluating browser script."
            if stderr.strip():
                timeout_message = f"{timeout_message} {stderr.strip()}"
            return None, timeout_message
        if proc.returncode == 0:
            return stdout.strip(), None
        else:
            return None, stderr.strip()
    except Exception as e:
        return None, str(e)
