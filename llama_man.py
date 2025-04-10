# llama_man.py
import os
import sys
import subprocess
import time
import signal
import llama_pid

# --- Determine Base Directory of this script ---
# __file__ is the path to the current script (llama_man.py)
# os.path.dirname gets the directory containing the script.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuration Paths Relative to this Script ---
# Construct absolute paths assuming bin/ and model/ are relative to llama_man.py
SERVER_PATH = os.path.join(_BASE_DIR, "bin/llama-b5061-bin-macos-x64/llama-server")
MODEL_PATH = os.path.join(_BASE_DIR, "model/gemma-3-1b-it-Q4_K_M.gguf")
# Note: Adjust the relative parts ("bin/...", "model/...") if your actual structure differs.

# --- Other Configuration ---
PORT = 8012
CTX_SIZE = 0
BATCH_SIZE = 1024
UB = 1024
CACHE_REUSE = 256
# --- End Configuration ---

# --- Server Management Functions ---

def start_llama_server():
    """
    Starts the llama-server process using paths relative to this script's location.
    Returns tuple (success: bool, message: str, pid: int | None).
    """
    pid = llama_pid.read_pid()
    if pid and llama_pid.is_process_running(pid):
        return False, f"Server already running with PID {pid}.", pid
    if pid and not llama_pid.is_process_running(pid):
        llama_pid.delete_pid_file()
        print(f"Cleaned up stale PID file for PID {pid}.")

    # Check the constructed absolute paths
    if not SERVER_PATH or not os.path.exists(SERVER_PATH):
       # The path is now absolute or relative to this file, error is more direct
       return False, f"Server executable path not found: '{SERVER_PATH}'. Ensure it exists relative to llama_man.py.", None
    if not MODEL_PATH or not os.path.exists(MODEL_PATH):
       return False, f"Model file path not found: '{MODEL_PATH}'. Ensure it exists relative to llama_man.py.", None

    # Command uses the calculated absolute paths
    command = [
        SERVER_PATH, '-m', MODEL_PATH, '--port', str(PORT),
        '--ctx-size', str(CTX_SIZE), '-b', str(BATCH_SIZE),
        '-ub', str(UB), '--cache-reuse', str(CACHE_REUSE)
    ]
    cmd_str = ' '.join(command)
    print(f"Attempting to start server with command: {cmd_str}")

    try:
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
            # Add creationflags=subprocess.CREATE_NO_WINDOW on Windows if STARTUPINFO isn't enough
            # creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        print(f"Launched process with PID: {process.pid}. Waiting briefly...")
        time.sleep(2.0)

        if process.poll() is not None:
             llama_pid.delete_pid_file()
             return False, f"Server process failed on startup (exit code {process.poll()}). Check server logs if possible. Command: {cmd_str}", None

        if not llama_pid.write_pid(process.pid):
             print(f"Warning: Server started (PID {process.pid}) but failed to write PID file.", file=sys.stderr)
             return True, f"Server started (PID {process.pid}) but failed to write PID file.", process.pid
        else:
            print(f"Server started successfully with PID {process.pid} and PID file written.")
            return True, f"Server started successfully with PID {process.pid}.", process.pid

    except FileNotFoundError:
        return False, f"Failed to start server: Executable not found at path '{SERVER_PATH}'. Check path and permissions.", None
    except PermissionError:
        return False, f"Failed to start server: Permission denied for executable at '{SERVER_PATH}'. Check permissions.", None
    except Exception as e:
        llama_pid.delete_pid_file()
        return False, f"Failed to start server process: {e}. Command: {cmd_str}", None

# stop_llama_server and status_llama_server remain unchanged from previous correct versions
def stop_llama_server(force=False):
    # ... (implementation unchanged) ...
    pid = llama_pid.read_pid()
    if not pid: return True, "Server not running (no PID file)."
    if not llama_pid.is_process_running(pid):
        msg = f"Stale PID {pid} found. Cleaning up PID file."
        llama_pid.delete_pid_file(); return True, msg
    stopped_gracefully = False
    try:
        sig = signal.SIGINT if sys.platform != 'win32' else signal.SIGBREAK
        os.kill(pid, sig)
        for _ in range(5):
            time.sleep(1);
            if not llama_pid.is_process_running(pid): stopped_gracefully = True; break
    except Exception as e:
        if not llama_pid.is_process_running(pid): stopped_gracefully = True
        elif not force: return False, f"Stop signal failed: {e}. Try --force."
    if stopped_gracefully:
        llama_pid.delete_pid_file(); return True, f"Server PID {pid} stopped gracefully."
    if not force: return False, f"Server PID {pid} did not stop gracefully. Use --force."
    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True, capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM); time.sleep(1)
            if llama_pid.is_process_running(pid): os.kill(pid, signal.SIGKILL); time.sleep(0.5)
        if not llama_pid.is_process_running(pid):
             llama_pid.delete_pid_file(); return True, f"Server PID {pid} terminated forcefully."
        else: return False, "Failed to force kill process."
    except Exception as e:
         if not llama_pid.is_process_running(pid):
             llama_pid.delete_pid_file(); return True, f"Force stop error but process died: {e}"
         return False, f"Force stop error: {e}"

def status_llama_server():
    # ... (implementation unchanged) ...
    pid = llama_pid.read_pid()
    if pid:
        if llama_pid.is_process_running(pid):
            return "RUNNING", f"Server is RUNNING with PID {pid}."
        else:
            llama_pid.delete_pid_file() # Clean up stale PID
            return "STALE_PID", f"Server is STOPPED (Stale PID {pid} found in '{llama_pid.PID_FILENAME}' and cleaned up)."
    else:
        return "STOPPED", f"Server is STOPPED (No PID file '{llama_pid.PID_FILENAME}' found)."


# ensure_server_running_or_fail remains unchanged (uses the modified start_llama_server)
def ensure_server_running_or_fail():
    """
    Checks server status, starts if needed using configured settings.
    Returns: Tuple (status_code: str, message: str)
    status_code can be "RUNNING", "FAILED_START"
    """
    status_code, initial_message = status_llama_server()

    if status_code == "RUNNING":
        return "RUNNING", initial_message

    print("Server not running or PID stale. Attempting auto-start...")
    success, start_message, pid = start_llama_server() # Uses new path logic

    if success:
        print(f"Auto-start successful: {start_message}")
        time.sleep(2.5)
        return "RUNNING", f"Auto-start successful: {start_message}"
    else:
        print(f"Error: Auto-start failed: {start_message}", file=sys.stderr)
        return "FAILED_START", f"Auto-start failed: {start_message}"