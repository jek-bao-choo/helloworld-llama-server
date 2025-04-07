# util.py
import os
import sys
import subprocess
import signal
import click  # Needed for secho in helper functions

# --- Configuration ---
PID_FILENAME = ".llama_server.pid"
DEFAULT_SERVER_PATH = "bin/llama-b5061-bin-macos-x64/llama-server"
DEFAULT_MODEL_PATH = "model/gemma-3-1b-it-Q4_K_M.gguf"
DEFAULT_PORT = 8012
DEFAULT_CONTEXT_SIZE = 0
DEFAULT_BATCH_SIZE = 1024
DEFAULT_UPLOAD_BUFFER = 1024
DEFAULT_CACHE_REUSE = 256
DEFAULT_LLAMA_SERVER_URL = f"http://127.0.0.1:{DEFAULT_PORT}/completion"

# --- Helper Functions ---

def _read_pid():
    """Reads the PID from the PID file, returns None if not found or invalid."""
    try:
        if os.path.exists(PID_FILENAME):
            with open(PID_FILENAME, 'r') as f:
                pid_str = f.read().strip()
                if pid_str:
                    return int(pid_str)
    except (IOError, ValueError) as e:
        # Use click's styled echo for consistency, even in util
        click.secho(f"Warning: Error reading PID file '{PID_FILENAME}': {e}", fg='yellow')
    return None

def _write_pid(pid):
    """Writes the PID to the PID file."""
    try:
        with open(PID_FILENAME, 'w') as f:
            f.write(str(pid))
    except IOError as e:
        click.secho(f"Error: Failed writing PID file '{PID_FILENAME}': {e}", fg='red')
        return False
    return True

def _delete_pid_file():
    """Deletes the PID file if it exists."""
    try:
        if os.path.exists(PID_FILENAME):
            os.remove(PID_FILENAME)
    except OSError as e:
        click.secho(f"Warning: Error deleting PID file '{PID_FILENAME}': {e}", fg='yellow')

def _is_process_running(pid):
    """Checks if a process with the given PID is running."""
    if pid is None:
        return False
    if sys.platform == 'win32':
        try:
            # Use CREATE_NO_WINDOW flag to prevent flashing console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            cmd = ['tasklist', '/FI', f'PID eq {pid}']
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo)
            # Basic check: does the PID appear in the output?
            return str(pid) in output
        except (subprocess.CalledProcessError, FileNotFoundError):
            # CalledProcessError if PID not found (tasklist returns error),
            # FileNotFoundError if tasklist isn't in PATH.
             return False
        except Exception as e:
            # Catch potential other errors during check
            click.secho(f"Warning: Windows process check failed for PID {pid}: {e}", fg='yellow')
            return False # Assume not running on error
    else: # Linux, macOS, other Unix-like
        try:
            # Signal 0 doesn't kill but checks existence/permissions
            os.kill(pid, 0)
        except OSError:
            # ESRCH -> No such process
            # EPERM -> Process exists but user lacks permissions (treat as running for status)
            # Let's assume if kill(pid, 0) fails with anything other than permission denied, it's not running.
            # A more precise check might use psutil, but os.kill is built-in.
             import errno
             if sys.exc_info()[1].errno == errno.EPERM:
                 return True # Process exists, but we lack permissions to signal it
             return False # Process doesn't exist or other error
        else:
            return True # Process exists