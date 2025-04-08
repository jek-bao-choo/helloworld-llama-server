# man_llama.py
import os
import sys
import subprocess
import time
import signal
import pid_llama
from config_loader import LLAMA_CONFIG # Import loaded config

def start_llama_server():
    """
    Starts the llama-server process using settings from config file.
    Returns tuple (success: bool, message: str, pid: int | None).
    """
    pid = pid_llama.read_pid()
    if pid and pid_llama.is_process_running(pid):
        return False, f"Server already running with PID {pid}.", pid

    if pid and not pid_llama.is_process_running(pid):
        pid_llama.delete_pid_file()

    # Use loaded config
    server_cfg = LLAMA_CONFIG
    server_path = server_cfg['server_path']
    model_path = server_cfg['model_path']

    if not server_path or not os.path.exists(server_path):
       return False, f"Server executable path missing or not found in config: {server_path}", None
    if not model_path or not os.path.exists(model_path):
       return False, f"Model file path missing or not found in config: {model_path}", None

    command = [
        server_path, '-m', model_path, '--port', str(server_cfg['port']),
        '--ctx-size', str(server_cfg['ctx_size']), '-b', str(server_cfg['batch_size']),
        '-ub', str(server_cfg['ub']), '--cache-reuse', str(server_cfg['cache_reuse'])
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

def stop_llama_server(force=False):
    """
    Stops the running llama-server process identified by the PID file.
    Returns tuple (success: bool, message: str).
    """
    # (Logic remains largely the same as previous version, uses pid_llama)
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
    Checks the status of the llama-server process using config.
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

# Removed restart_llama_server as CLI command is removed.