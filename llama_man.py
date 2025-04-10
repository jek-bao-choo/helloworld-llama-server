# llama_man.py
import os
import sys
import subprocess
import time       # Keep time for sleep after start
import signal
# REMOVED: import click
import llama_pid  # Keep updated import

# --- Hardcoded Configuration ---
SERVER_PATH = "bin/llama-b5061-bin-macos-x64/llama-server"
MODEL_PATH = "model/gemma-3-1b-it-Q4_K_M.gguf"
PORT = 8012 # Export PORT so cli_server can build URL
CTX_SIZE = 0
BATCH_SIZE = 1024
UB = 1024
CACHE_REUSE = 256
# --- End Hardcoded Configuration ---

# --- Server Management Functions ---
# start_llama_server, stop_llama_server, status_llama_server remain unchanged from previous step

def start_llama_server():
    """
    Starts the llama-server process using hardcoded settings.
    Returns tuple (success: bool, message: str, pid: int | None).
    """
    # ... (implementation unchanged) ...
    pid = llama_pid.read_pid()
    if pid and llama_pid.is_process_running(pid):
        return False, f"Server already running with PID {pid}.", pid
    if pid and not llama_pid.is_process_running(pid):
        llama_pid.delete_pid_file()
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
        time.sleep(2.0)
        if process.poll() is not None:
             llama_pid.delete_pid_file()
             return False, f"Server process failed on startup (exit code {process.poll()}). Command: {cmd_str}", None
        if not llama_pid.write_pid(process.pid):
            return True, f"Server started (PID {process.pid}) but failed to write PID file.", process.pid
        else:
            return True, f"Server started successfully with PID {process.pid}.", process.pid
    except Exception as e:
        llama_pid.delete_pid_file()
        return False, f"Failed to start server process: {e}. Command: {cmd_str}", None

def stop_llama_server(force=False):
    """
    Stops the running llama-server process identified by the PID file.
    Returns tuple (success: bool, message: str).
    """
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
    """
    Checks the status of the llama-server process.
    Returns tuple (status_string: str, message: str).
    """
    # ... (implementation unchanged) ...
    pid = llama_pid.read_pid()
    if pid:
        if llama_pid.is_process_running(pid):
            return "RUNNING", f"Server is RUNNING with PID {pid}."
        else:
            return "STALE_PID", f"Server is STOPPED (Stale PID {pid} found in '{llama_pid.PID_FILENAME}')."
    else:
        return "STOPPED", f"Server is STOPPED (No PID file '{llama_pid.PID_FILENAME}' found)."


# --- Refactored Helper Function ---
def ensure_server_running_or_fail():
    """
    Checks server status, starts if needed using internal defaults.
    No direct user feedback here (no click dependency).

    Returns:
        Tuple (status_code: str, message: str)
        status_code can be "RUNNING", "FAILED_START"
    """
    status_code, initial_message = status_llama_server()
    # Don't print here - let the caller (cli_server) do it.
    # click.echo(f"Initial server status: {status_code} - {initial_message}")

    if status_code == "RUNNING":
        return "RUNNING", initial_message # Return immediately if already running

    # If STOPPED or STALE_PID, attempt to start
    # Don't print here: click.echo("Server not running. Attempting auto-start...")
    success, start_message, pid = start_llama_server() # Uses internal config

    if success:
        # Don't print here: click.secho(f"Auto-start successful: {start_message}", fg='green')
        time.sleep(2.5) # Keep brief pause after successful start
        # Return RUNNING status and the success message from start_llama_server
        return "RUNNING", f"Auto-start successful: {start_message}"
    else:
        # Don't print here: click.secho(f"Auto-start failed: {start_message}", fg='red')
        # Return FAILED status and the error message from start_llama_server
        return "FAILED_START", f"Auto-start failed: {start_message}"
# --- End Refactored Helper ---