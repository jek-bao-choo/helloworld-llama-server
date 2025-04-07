# cli.py
import click
import requests
import json
import subprocess
import os
import sys
import time
import signal

# Import constants and helpers from util.py using relative import
from util import (
    PID_FILENAME, DEFAULT_SERVER_PATH, DEFAULT_MODEL_PATH, DEFAULT_PORT,
    DEFAULT_CONTEXT_SIZE, DEFAULT_BATCH_SIZE, DEFAULT_UPLOAD_BUFFER,
    DEFAULT_CACHE_REUSE, DEFAULT_LLAMA_SERVER_URL,
    _read_pid, _write_pid, _delete_pid_file, _is_process_running
)

# --- Click Command Group ---

@click.group()
def cli():
    """A CLI tool to interact with and manage a local llama-server."""
    pass

# --- Server Management Commands ---

@cli.command()
@click.option('--server-path', default=DEFAULT_SERVER_PATH, help='Path to the llama-server executable.')
@click.option('--model', default=DEFAULT_MODEL_PATH, help='Path to the GGUF model file.')
@click.option('--port', default=DEFAULT_PORT, type=int, help='Port for llama-server to listen on.')
@click.option('--ctx-size', default=DEFAULT_CONTEXT_SIZE, type=int, help='Context size for the model (0=model default).')
@click.option('--batch-size', '-b', default=DEFAULT_BATCH_SIZE, type=int, help='Batch size for prompt processing.')
@click.option('--ub', default=DEFAULT_UPLOAD_BUFFER, type=int, help='Upload buffer size.')
@click.option('--cache-reuse', default=DEFAULT_CACHE_REUSE, type=int, help='Amount of cache to reuse.')
def start(server_path, model, port, ctx_size, batch_size, ub, cache_reuse):
    """Starts the llama-server process in the background."""
    pid = _read_pid()
    if pid and _is_process_running(pid):
        click.echo(f"Server seems to be already running with PID {pid} (found in '{PID_FILENAME}').")
        return

    if pid and not _is_process_running(pid):
        click.secho(f"Found stale PID file for non-running process {pid}. Removing it.", fg='yellow')
        _delete_pid_file()

    if not os.path.exists(server_path):
       click.secho(f"Error: Server executable not found at '{server_path}'. Check path.", fg='red')
       return
    if not os.path.exists(model):
       click.secho(f"Error: Model file not found at '{model}'. Check path.", fg='red')
       return

    command = [
        server_path, '-m', model, '--port', str(port), '--ctx-size', str(ctx_size),
        '-b', str(batch_size), '-ub', str(ub), '--cache-reuse', str(cache_reuse)
    ]
    click.echo(f"Starting server with command: {' '.join(command)}")

    try:
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo
        )
        time.sleep(1.5)

        if process.poll() is not None:
             click.secho(f"Server process terminated unexpectedly (exit code: {process.poll()}).", fg='red')
             _delete_pid_file()
             return

        if not _write_pid(process.pid):
             click.secho("Warning: Failed to write PID file. Server started but 'stop' might fail.", fg='yellow')
        else:
             click.echo(f"Server started successfully with PID {process.pid}.")
             click.echo(f"PID stored in '{PID_FILENAME}'. Listening on port {port}.")

    except FileNotFoundError:
        click.secho(f"Error: Could not execute command. Is '{server_path}' correct?", fg='red')
    except Exception as e:
        click.secho(f"An unexpected error occurred while starting the server: {e}", fg='red')
        _delete_pid_file()

@cli.command()
def status():
    """Checks if the llama-server process is running."""
    pid = _read_pid()
    if pid:
        if _is_process_running(pid):
            click.echo(f"Server is RUNNING with PID {pid} (according to '{PID_FILENAME}').")
        else:
            click.secho(f"Server is STOPPED (PID {pid} found in '{PID_FILENAME}', but process not running).", fg='yellow')
            click.echo("Consider running 'start' or manually deleting the PID file.")
    else:
        click.echo(f"Server is STOPPED (No PID file '{PID_FILENAME}' found).")

@cli.command()
@click.option('--force', is_flag=True, help='Force stop using SIGKILL/TerminateProcess if graceful stop fails.')
def stop(force):
    """Stops the running llama-server process."""
    pid = _read_pid()
    if not pid:
        click.echo("Server is not running (no PID file found).")
        return

    if not _is_process_running(pid):
        click.secho(f"Server process with PID {pid} not found. Cleaning up PID file.", fg='yellow')
        _delete_pid_file()
        return

    click.echo(f"Attempting to gracefully stop server process with PID {pid}...")

    graceful_signal = signal.SIGINT if sys.platform != 'win32' else signal.SIGBREAK # Try SIGBREAK on Win
    try:
        os.kill(pid, graceful_signal)
    except ProcessLookupError:
         click.secho(f"Process {pid} not found (already stopped?).", fg='yellow')
         _delete_pid_file()
         return
    except Exception as e:
         click.secho(f"Could not send graceful signal ({graceful_signal}) to PID {pid}: {e}", fg='red')
         if not force: return

    attempts = 5
    stopped = False
    for i in range(attempts):
        time.sleep(1)
        if not _is_process_running(pid):
            stopped = True
            break
        click.echo(f"Waiting for server to stop... ({i+1}/{attempts})")

    if stopped:
        click.echo(f"Server process {pid} stopped successfully.")
        _delete_pid_file()
    else:
        click.secho(f"Server process {pid} did not stop gracefully.", fg='yellow')
        if force:
            click.secho("Forcing termination...", fg='yellow')
            try:
                if sys.platform == 'win32':
                    # Use taskkill /F for forced termination on Windows
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True, capture_output=True)
                else:
                    os.kill(pid, signal.SIGTERM) # Try SIGTERM first
                    time.sleep(1)
                    if _is_process_running(pid):
                         os.kill(pid, signal.SIGKILL) # SIGKILL as last resort
                         time.sleep(0.5)

                if not _is_process_running(pid):
                     click.echo(f"Server process {pid} terminated forcefully.")
                     _delete_pid_file()
                else:
                     click.secho(f"Failed to force kill process {pid}.", fg='red')

            except (subprocess.CalledProcessError, OSError) as e:
                 click.secho(f"Error during force termination of PID {pid}: {e}", fg='red')
                 if not _is_process_running(pid): _delete_pid_file() # Cleanup if it died anyway
            except Exception as e:
                 click.secho(f"Unexpected error during force termination: {e}", fg='red')
        else:
            click.echo("Consider using --force option.")


@cli.command()
@click.option('--server-path', default=DEFAULT_SERVER_PATH, help='Path to the llama-server executable.')
@click.option('--model', default=DEFAULT_MODEL_PATH, help='Path to the GGUF model file.')
@click.option('--port', default=DEFAULT_PORT, type=int, help='Port for llama-server to listen on.')
@click.option('--ctx-size', default=DEFAULT_CONTEXT_SIZE, type=int, help='Context size.')
@click.option('--batch-size', '-b', default=DEFAULT_BATCH_SIZE, type=int, help='Batch size.')
@click.option('--ub', default=DEFAULT_UPLOAD_BUFFER, type=int, help='Upload buffer size.')
@click.option('--cache-reuse', default=DEFAULT_CACHE_REUSE, type=int, help='Cache reuse amount.')
@click.pass_context
def restart(ctx, server_path, model, port, ctx_size, batch_size, ub, cache_reuse):
    """Stops and then starts the llama-server process."""
    click.echo("--- Attempting to stop server ---")
    ctx.invoke(stop, force=True)
    click.echo("\n--- Attempting to start server ---")
    time.sleep(1)
    ctx.invoke(start, server_path=server_path, model=model, port=port,
               ctx_size=ctx_size, batch_size=batch_size, ub=ub,
               cache_reuse=cache_reuse)


# --- Interaction Command ---

@cli.command()
@click.option('--prompt', default="Hello", help='The prompt to send to the llama server.')
@click.option('--server-url', default=DEFAULT_LLAMA_SERVER_URL, help='URL of the llama-server completion endpoint.')
def send_prompt(prompt, server_url):
    """Sends a simple prompt to a running llama-server."""
    pid = _read_pid()
    # Optional: check if running before sending request
    # if not (pid and _is_process_running(pid)):
    #      click.secho("Server process not detected. Use 'start' first.", fg='yellow')
         # return # Or maybe try anyway?

    click.echo(f"Sending prompt to: {server_url}")
    # click.echo(f"Prompt: {prompt}") # Maybe redundant if user typed it

    payload = {"prompt": prompt, "n_predict": -1} # -1 as a signal to generate tokens until either the model naturally stops (EOS) or the context window limit (--ctx-size) is reached
    response = None # Define response outside try block for access in json error

    try:
        response = requests.post(
            server_url, headers={"Content-Type": "application/json"}, json=payload, timeout=90
        )
        response.raise_for_status()
        result = response.json()
        click.echo("\n--- Server Response ---")
        if 'content' in result:
            click.echo(result['content'].strip())
        else:
            click.echo(json.dumps(result, indent=2)) # Pretty print if no 'content' key
        click.echo("-----------------------\n")

    except requests.exceptions.ConnectionError:
        click.secho(f"Error: Connection refused at {server_url}.", fg='red')
        click.secho("=> Is the server running? Use 'status' or 'start'.", fg='yellow')
    except requests.exceptions.Timeout:
        click.secho(f"Error: Request timed out connecting to {server_url}.", fg='red')
    except requests.exceptions.RequestException as e:
        click.secho(f"Error during request to {server_url}: {e}", fg='red')
        if e.response is not None:
            click.secho(f"Server raw response: {e.response.text}", fg='red')
    except json.JSONDecodeError:
        raw_response_text = response.text if response else "No response received"
        click.secho(f"Error: Could not decode JSON response from server.", fg='red')
        click.secho(f"Raw response: {raw_response_text}", fg='red')