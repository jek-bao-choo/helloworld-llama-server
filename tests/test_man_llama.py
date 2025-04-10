# tests/test_man_llama.py

import pytest
import subprocess
import time
import os
import sys
import signal
from unittest.mock import MagicMock # Useful for creating mock objects like Popen return

# Modules to test and mock
import llama_man
import llama_pid
# Import config_loader only to potentially mock its variables if needed,
# but we prefer patching the variable where it's used (in man_llama)
# import config_loader

# --- Mock Configuration ---
# Create a dictionary representing the config loaded from config_loader
MOCK_LLAMA_CONFIG = {
    'server_path': '/fake/path/to/server',
    'model_path': '/fake/path/to/model.gguf',
    'port': 8099,
    'ctx_size': 1024,
    'batch_size': 512,
    'ub': 512,
    'cache_reuse': 128,
}

# --- Tests for status_llama_server ---

def test_status_server_running(mocker):
    """Test status when server is running."""
    mocker.patch('man_llama.pid_llama.read_pid', return_value=123)
    mocker.patch('man_llama.pid_llama.is_process_running', return_value=True)

    status, message = llama_man.status_llama_server()

    assert status == "RUNNING"
    assert "Server is RUNNING with PID 123" in message

def test_status_server_stopped_no_pid(mocker):
    """Test status when server stopped (no PID file)."""
    mocker.patch('man_llama.pid_llama.read_pid', return_value=None)
    # Mock is_process_running to ensure it's not called if read_pid is None
    mock_is_running = mocker.patch('man_llama.pid_llama.is_process_running')

    status, message = llama_man.status_llama_server()

    assert status == "STOPPED"
    assert "No PID file" in message
    mock_is_running.assert_not_called()

def test_status_server_stale_pid(mocker):
    """Test status when PID file exists but process is not running."""
    mocker.patch('man_llama.pid_llama.read_pid', return_value=456)
    mocker.patch('man_llama.pid_llama.is_process_running', return_value=False)

    status, message = man_llama.status_llama_server()

    assert status == "STALE_PID"
    assert "Stale PID 456" in message

# --- Tests for start_llama_server ---

def test_start_server_already_running(mocker):
    """Test start when server is already running."""
    # Patch the imported config directly within the man_llama module's namespace
    mocker.patch('man_llama.LLAMA_CONFIG', MOCK_LLAMA_CONFIG)
    mocker.patch('man_llama.pid_llama.read_pid', return_value=123)
    mocker.patch('man_llama.pid_llama.is_process_running', return_value=True)
    mock_popen = mocker.patch('subprocess.Popen') # Check it's not called

    success, message, pid = llama_man.start_llama_server()

    assert not success
    assert "already running" in message
    assert pid == 123
    mock_popen.assert_not_called()

def test_start_server_success(mocker):
    """Test successful server start."""
    # Patch config used by the function
    mocker.patch('man_llama.LLAMA_CONFIG', MOCK_LLAMA_CONFIG)
    # Mock PID checks to indicate not running initially
    mocker.patch('man_llama.pid_llama.read_pid', return_value=None)
    # Mock filesystem checks
    mocker.patch('os.path.exists', return_value=True)
    # Mock subprocess.Popen
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 789
    mock_process.poll.return_value = None # Indicate process is running after sleep
    mock_popen = mocker.patch('subprocess.Popen', return_value=mock_process)
    # Mock time.sleep to avoid actual waiting
    mocker.patch('time.sleep')
    # Mock successful PID write
    mock_write_pid = mocker.patch('man_llama.pid_llama.write_pid', return_value=True)

    success, message, pid = llama_man.start_llama_server()

    assert success
    assert "started successfully" in message
    assert pid == 789
    # Verify Popen was called with expected args based on MOCK_LLAMA_CONFIG
    expected_cmd = [
        MOCK_LLAMA_CONFIG['server_path'], '-m', MOCK_LLAMA_CONFIG['model_path'],
        '--port', str(MOCK_LLAMA_CONFIG['port']), '--ctx-size', str(MOCK_LLAMA_CONFIG['ctx_size']),
        '-b', str(MOCK_LLAMA_CONFIG['batch_size']), '-ub', str(MOCK_LLAMA_CONFIG['ub']),
        '--cache-reuse', str(MOCK_LLAMA_CONFIG['cache_reuse'])
    ]
    mock_popen.assert_called_once()
    call_args, call_kwargs = mock_popen.call_args
    assert call_args[0] == expected_cmd # Check command list
    assert call_kwargs.get('stdout') == subprocess.DEVNULL
    assert call_kwargs.get('stderr') == subprocess.DEVNULL
    # Verify PID write was called
    mock_write_pid.assert_called_once_with(789)

def test_start_server_path_not_found(mocker):
    """Test start when server executable path doesn't exist."""
    mocker.patch('man_llama.LLAMA_CONFIG', MOCK_LLAMA_CONFIG)
    mocker.patch('man_llama.pid_llama.read_pid', return_value=None)
    # Mock os.path.exists: return False only for server_path
    # Note: This side_effect needs careful checking if more paths were added
    mocker.patch('os.path.exists', side_effect=lambda path: path != MOCK_LLAMA_CONFIG['server_path'])

    success, message, pid = llama_man.start_llama_server()

    assert not success
    # Update the string we are checking for:
    assert "Server executable path missing or not found in config" in message # <-- CORRECTED ASSERTION
    assert pid is None

def test_start_server_immediate_fail(mocker):
    """Test start when the server process fails immediately."""
    mocker.patch('man_llama.LLAMA_CONFIG', MOCK_LLAMA_CONFIG)
    mocker.patch('man_llama.pid_llama.read_pid', return_value=None)
    mocker.patch('os.path.exists', return_value=True)
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 789
    mock_process.poll.return_value = 1 # Indicate process exited with error code 1
    mocker.patch('subprocess.Popen', return_value=mock_process)
    mocker.patch('time.sleep')
    mock_delete_pid = mocker.patch('man_llama.pid_llama.delete_pid_file')

    success, message, pid = llama_man.start_llama_server()

    assert not success
    assert "failed on startup (exit code 1)" in message
    assert pid is None
    mock_delete_pid.assert_called_once() # Should clean up if it wrote PID before poll check

# --- Tests for stop_llama_server ---

def test_stop_server_not_running_no_pid(mocker):
    """Test stop when server isn't running (no PID file)."""
    mocker.patch('man_llama.pid_llama.read_pid', return_value=None)
    mock_kill = mocker.patch('os.kill')

    success, message = man_llama.stop_llama_server()

    assert success
    assert "no PID file" in message
    mock_kill.assert_not_called()

def test_stop_server_stale_pid(mocker):
    """Test stop when PID file exists but process isn't running."""
    mocker.patch('man_llama.pid_llama.read_pid', return_value=456)
    mocker.patch('man_llama.pid_llama.is_process_running', return_value=False)
    mock_delete_pid = mocker.patch('man_llama.pid_llama.delete_pid_file')
    mock_kill = mocker.patch('os.kill')

    success, message = llama_man.stop_llama_server()

    assert success
    assert "Stale PID 456" in message
    mock_delete_pid.assert_called_once()
    mock_kill.assert_not_called()

def test_stop_server_graceful_success_unix(mocker):
    """Test successful graceful stop on Unix."""
    mocker.patch('sys.platform', 'linux') # Mock platform
    mocker.patch('man_llama.pid_llama.read_pid', return_value=123)
    # Simulate process running initially, then stopping after sleep
    mock_is_running = mocker.patch('man_llama.pid_llama.is_process_running', side_effect=[True, False])
    mock_kill = mocker.patch('os.kill')
    mocker.patch('time.sleep')
    mock_delete_pid = mocker.patch('man_llama.pid_llama.delete_pid_file')

    success, message = llama_man.stop_llama_server(force=False)

    assert success
    assert "stopped gracefully" in message
    mock_kill.assert_called_once_with(123, signal.SIGINT)
    mock_delete_pid.assert_called_once()
    assert mock_is_running.call_count == 2 # Initial check + check after sleep

def test_stop_server_graceful_fail_no_force(mocker):
    """Test graceful stop fails and force is False."""
    mocker.patch('sys.platform', 'linux')
    mocker.patch('man_llama.pid_llama.read_pid', return_value=123)
    # Simulate process never stopping
    mocker.patch('man_llama.pid_llama.is_process_running', return_value=True)
    mock_kill = mocker.patch('os.kill')
    mock_sleep = mocker.patch('time.sleep')
    mock_delete_pid = mocker.patch('man_llama.pid_llama.delete_pid_file')
    mock_subprocess_run = mocker.patch('subprocess.run') # For potential force kill

    success, message = llama_man.stop_llama_server(force=False)

    assert not success
    assert "did not stop gracefully" in message
    mock_kill.assert_called_once_with(123, signal.SIGINT) # Should have tried graceful
    assert mock_sleep.call_count == 5 # Should have waited 5 times
    mock_delete_pid.assert_not_called()
    mock_subprocess_run.assert_not_called() # Ensure force kill wasn't attempted
    # Ensure SIGTERM/KILL weren't attempted on os.kill mock
    assert all(call.args[1] == signal.SIGINT for call in mock_kill.call_args_list)


def test_stop_server_force_success_windows(mocker):
    """Test graceful fail, then successful force stop on Windows."""
    mocker.patch('sys.platform', 'win32')
    mocker.patch('man_llama.pid_llama.read_pid', return_value=123)

    # --- CORRECTED side_effect list ---
    # Needs 1 initial True + 5 Trues for the wait loop + 1 final False after force kill
    mock_is_running = mocker.patch(
        'man_llama.pid_llama.is_process_running',
        side_effect=[True] * 6 + [False] # 6 Trues, then False
    )
    # --- End Correction ---

    mock_kill = mocker.patch('os.kill') # Mock for graceful SIGBREAK attempt
    mock_sleep = mocker.patch('time.sleep')
    mock_delete_pid = mocker.patch('man_llama.pid_llama.delete_pid_file')
    # Mock successful taskkill - basic mock is fine, it just needs to not raise error for check=True
    mock_subprocess_run = mocker.patch('subprocess.run')

    success, message = man_llama.stop_llama_server(force=True)

    # --- Assertion should now pass ---
    assert success
    # --- End Assertion ---

    assert "terminated forcefully" in message
    # Check graceful attempt
    mock_kill.assert_called_once_with(123, signal.SIGBREAK)
    assert mock_sleep.call_count == 5 # Waited 5 times
    # Check force attempt
    mock_subprocess_run.assert_called_once_with(
        ['taskkill', '/F', '/PID', '123'], check=True, capture_output=True
    )
    # Check PID file deletion
    mock_delete_pid.assert_called_once()
    # Check is_process_running call count (initial + loop + after force)
    assert mock_is_running.call_count == 7