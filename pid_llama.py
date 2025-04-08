# pid_llama.py
import os
import sys
import subprocess
import errno

PID_FILENAME = ".llama_server.pid"

def read_pid():
    """Reads the PID from the PID file. Returns integer PID or None."""
    try:
        if os.path.exists(PID_FILENAME):
            with open(PID_FILENAME, 'r') as f:
                pid_str = f.read().strip()
                if pid_str:
                    return int(pid_str)
    except (IOError, ValueError):
        pass
    return None

def write_pid(pid):
    """Writes the PID to the PID file. Returns True on success, False on error."""
    try:
        with open(PID_FILENAME, 'w') as f:
            f.write(str(pid))
        return True
    except IOError:
        return False

def delete_pid_file():
    """Deletes the PID file if it exists. Returns True if deleted or not found, False on error."""
    try:
        if os.path.exists(PID_FILENAME):
            os.remove(PID_FILENAME)
        return True
    except OSError:
        return False

def is_process_running(pid):
    """Checks if a process with the given PID is running. Returns True/False."""
    if pid is None:
        return False
    if sys.platform == 'win32':
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            cmd = ['tasklist', '/FI', f'PID eq {pid}']
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo)
            return str(pid) in output
        except (subprocess.CalledProcessError, FileNotFoundError):
             return False
        except Exception:
            return False
    else: # Linux, macOS, other Unix-like
        try:
            os.kill(pid, 0)
        except OSError as err:
            if err.errno == errno.EPERM:
                return True
            return False
        else:
            return True