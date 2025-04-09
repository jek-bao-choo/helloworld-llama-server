# man_llama.py
import os
import sys
import subprocess
import time
import signal
import pid_llama
# REMOVED: from config_loader import LLAMA_CONFIG

# --- Hardcoded Configuration ---
# Values copied from previous config.yaml - MODIFY THESE PATHS/VALUES AS NEEDED
SERVER_PATH = "bin/llama-b5061-bin-macos-x64/llama-server"
MODEL_PATH = "model/gemma-3-1b-it-Q4_K_M.gguf"
PORT = 8012
CTX_SIZE = 0
BATCH_SIZE = 1024
UB = 1024
CACHE_REUSE = 256
# --- End Hardcoded Configuration ---

def start_llama_server():
    """
    Starts the llama-server process using hardcoded settings.
    Returns tuple (success: bool, message: str, pid: int | None).
    """
    pid = pid_llama.read_pid()
    if pid and pid_llama.is_process_running(pid):
        return False, f"Server already running with PID {pid}.", pid

    if pid and not pid_llama.is_process_running(pid):
        pid_llama.delete_pid_file()

    # Use constants defined above
    if not SERVER_PATH or not os.path.exists(SERVER_PATH):
       return False, f"Server executable path not found or not configured: {SERVER_PATH}", None
    if not MODEL_PATH or not os.path.exists(MODEL_PATH):
       return False, f"Model file path not found or not configured: {MODEL_PATH}", None

    command = [
        SERVER_PATH, '-m', MODEL_PATH, '--port', str(PORT),
        '--ctx-size', str(CTX_SIZE), '-b', str(BATCH_SIZE),
        '-ub', str(UB), '--cache-reuse', str(CACHE_REUSE)
    ]
    cmd_str = ' '.join(command)

    try:
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo
        )
        time.sleep(2.0) # Allow time to start/fail

        if process.poll() is not None:
             pid_llama.delete_pid_file()
             return False, f"Server process failed on startup (exit code {process.poll()}). Command: {cmd_str}", None

        if not pid_llama.write_pid(process.pid):
            return True, f"Server started (PID {process.pid}) but failed to write PID file.", process.pid
        else:
            return True, f"Server started successfully with PID {process.pid}.", process.pid

    except Exception as e:
        pid_llama.delete_pid_file()
        return False, f"Failed to start server process: {e}. Command: {cmd_str}", None

# --- stop_llama_server and status_llama_server remain unchanged ---
# They primarily interact with pid_llama, not the start configuration.

def stop_llama_server(force=False):
    """
    Stops the running llama-server process identified by the PID file.
    Returns tuple (success: bool, message: str).
    """
    # (Logic remains the same as previous version, uses pid_llama)
    pid = pid_llama.read_pid()
    if not pid: return True, "Server not running (no PID file)."
    if not pid_llama.is_process_running(pid):
        msg = f"Stale PID {pid} found. Cleaning up PID file."
        pid_llama.delete_pid_file(); return True, msg

    stopped_gracefully = False
    try:
        sig = signal.SIGINT if sys.platform != 'win32' else signal.SIGBREAK
        os.kill(pid, sig)
        for _ in range(5):
            time.sleep(1);
            if not pid_llama.is_process_running(pid): stopped_gracefully = True; break
    except Exception as e:
        if not pid_llama.is_process_running(pid): stopped_gracefully = True
        elif not force: return False, f"Stop signal failed: {e}. Try --force."

    if stopped_gracefully:
        pid_llama.delete_pid_file(); return True, f"Server PID {pid} stopped gracefully."
    if not force: return False, f"Server PID {pid} did not stop gracefully. Use --force."

    # Force stop
    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True, capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM); time.sleep(1)
            if pid_llama.is_process_running(pid): os.kill(pid, signal.SIGKILL); time.sleep(0.5)
        if not pid_llama.is_process_running(pid):
             pid_llama.delete_pid_file(); return True, f"Server PID {pid} terminated forcefully."
        else: return False, "Failed to force kill process."
    except Exception as e:
         if not pid_llama.is_process_running(pid):
             pid_llama.delete_pid_file(); return True, f"Force stop error but process died: {e}"
         return False, f"Force stop error: {e}"

def status_llama_server():
    """
    Checks the status of the llama-server process.
    Returns tuple (status_string: str, message: str).
    """
    # (Logic remains the same, uses pid_llama)
    pid = pid_llama.read_pid()
    if pid:
        if pid_llama.is_process_running(pid):
            return "RUNNING", f"Server is RUNNING with PID {pid}."
        else:
            return "STALE_PID", f"Server is STOPPED (Stale PID {pid} found in '{pid_llama.PID_FILENAME}')."
    else:
        return "STOPPED", f"Server is STOPPED (No PID file '{pid_llama.PID_FILENAME}' found)."