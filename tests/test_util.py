# tests/test_util.py

import pytest
import subprocess
import errno
from unittest.mock import MagicMock # Can be useful alongside mocker

# Import the module we are testing
# Use 'util' because we're running pytest from the root my_llama_cli dir
# and have __init__.py files potentially making things importable.
# If this fails, try absolute path based on your project structure if needed.
import util

# --- Tests for _read_pid ---

def test_read_pid_file_exists_valid(mocker):
    """Test _read_pid when PID file exists and contains a valid PID."""
    # Mock os.path.exists to return True
    mocker.patch('os.path.exists', return_value=True)
    # Mock the built-in open function to simulate reading '12345' from the file
    mock_file = mocker.mock_open(read_data='12345')
    mocker.patch('builtins.open', mock_file)

    pid = util._read_pid()

    # Assertions
    assert pid == 12345
    mock_file.assert_called_once_with(util.PID_FILENAME, 'r')

def test_read_pid_file_not_exist(mocker):
    """Test _read_pid when PID file does not exist."""
    mocker.patch('os.path.exists', return_value=False)
    mock_open = mocker.patch('builtins.open') # Mock open to check it wasn't called

    pid = util._read_pid()

    assert pid is None
    mock_open.assert_not_called() # Ensure open wasn't called if file doesn't exist

def test_read_pid_file_exists_empty(mocker):
    """Test _read_pid when PID file exists but is empty."""
    mocker.patch('os.path.exists', return_value=True)
    mock_file = mocker.mock_open(read_data='')
    mocker.patch('builtins.open', mock_file)

    pid = util._read_pid()

    assert pid is None

def test_read_pid_file_invalid_content(mocker):
    """Test _read_pid when PID file contains non-integer data."""
    mocker.patch('os.path.exists', return_value=True)
    mock_file = mocker.mock_open(read_data='not-a-pid')
    mocker.patch('builtins.open', mock_file)
    # Mock secho to prevent it from printing during tests (optional)
    mocker.patch('click.secho')

    pid = util._read_pid()

    assert pid is None # Should fail int conversion

def test_read_pid_io_error(mocker):
    """Test _read_pid when an IOError occurs during file reading."""
    mocker.patch('os.path.exists', return_value=True)
    # Mock open to raise an IOError when called
    mocker.patch('builtins.open', side_effect=IOError("Disk read error"))
    mocker.patch('click.secho') # Mock secho

    pid = util._read_pid()

    assert pid is None

# --- Tests for _write_pid ---

def test_write_pid_success(mocker):
    """Test _write_pid successful write."""
    mock_file = mocker.mock_open()
    mocker.patch('builtins.open', mock_file)
    test_pid = 54321

    result = util._write_pid(test_pid)

    assert result is True
    # Check that open was called correctly
    mock_file.assert_called_once_with(util.PID_FILENAME, 'w')
    # Check that write was called on the file handle with the PID as a string
    handle = mock_file()
    handle.write.assert_called_once_with(str(test_pid))

def test_write_pid_io_error(mocker):
    """Test _write_pid when an IOError occurs."""
    # Mock open to raise an IOError
    mocker.patch('builtins.open', side_effect=IOError("Permission denied"))
    mocker.patch('click.secho') # Mock secho
    test_pid = 54321

    result = util._write_pid(test_pid)

    assert result is False

# --- Tests for _delete_pid_file ---

def test_delete_pid_file_exists(mocker):
    """Test _delete_pid_file when the file exists."""
    mocker.patch('os.path.exists', return_value=True)
    mock_remove = mocker.patch('os.remove')

    util._delete_pid_file()

    mock_remove.assert_called_once_with(util.PID_FILENAME)

def test_delete_pid_file_not_exists(mocker):
    """Test _delete_pid_file when the file does not exist."""
    mocker.patch('os.path.exists', return_value=False)
    mock_remove = mocker.patch('os.remove')

    util._delete_pid_file()

    mock_remove.assert_not_called()

def test_delete_pid_file_os_error(mocker):
    """Test _delete_pid_file when os.remove raises an error."""
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.remove', side_effect=OSError("Cannot delete"))
    mocker.patch('click.secho') # Mock secho

    # We just call it, expecting no exception, but a warning would be logged
    util._delete_pid_file()


# --- Tests for _is_process_running ---

def test_is_process_running_pid_none():
    """Test _is_process_running with pid=None."""
    assert util._is_process_running(None) is False

# Use pytest.mark.parametrize to test different platforms easily
@pytest.mark.parametrize("platform, mock_os_kill_effect, expected", [
    ('linux', None, True),                     # Linux, process exists (os.kill succeeds)
    ('darwin', None, True),                    # macOS, process exists
    ('linux', OSError(errno.ESRCH, "No such process"), False), # Linux, process doesn't exist
    ('linux', OSError(errno.EPERM, "Permission denied"), True), # Linux, process exists but no permission
])
def test_is_process_running_unix(mocker, platform, mock_os_kill_effect, expected):
    """Test _is_process_running on Unix-like systems."""
    mocker.patch('sys.platform', platform) # Mock the platform
    mock_kill = mocker.patch('os.kill', side_effect=mock_os_kill_effect) # Mock os.kill behavior
    test_pid = 123

    result = util._is_process_running(test_pid)

    assert result == expected
    # Ensure os.kill was called if an effect was specified or expected True
    if mock_os_kill_effect is not None or expected:
         mock_kill.assert_called_once_with(test_pid, 0)

# Parametrize for Windows scenarios
@pytest.mark.parametrize("mock_check_output_effect, expected", [
    ("PID: 123", True),                         # Windows, tasklist finds PID
    (subprocess.CalledProcessError(1, "tasklist", output=b"INFO: No tasks running."), False), # Windows, tasklist doesn't find PID
    (FileNotFoundError, False),                 # Windows, tasklist command not found
    (Exception("Some other error"), False)      # Windows, other unexpected error
])
def test_is_process_running_windows(mocker, mock_check_output_effect, expected):
    """Test _is_process_running on Windows."""
    mocker.patch('sys.platform', 'win32') # Mock platform to Windows
    # Mock subprocess.check_output behavior
    mock_check = mocker.patch('subprocess.check_output', side_effect=mock_check_output_effect)
     # Mock STARTUPINFO if needed, though check_output mock bypasses its direct use here
    mocker.patch('subprocess.STARTUPINFO', return_value=MagicMock())

    test_pid = 123
    result = util._is_process_running(test_pid)

    assert result == expected
    # Expect check_output to be called unless the effect is None (though we don't have that case here)
    if mock_check_output_effect is not None:
        mock_check.assert_called_once()
        # Could add assertion on the specific command called if needed
        # assert mock_check.call_args[0][0] == ['tasklist', '/FI', f'PID eq {test_pid}']