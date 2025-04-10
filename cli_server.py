# cli_server.py
import click
import sys
import requests # For making HTTP requests
import json     # For parsing JSON data from SSE

# Import server management functions and config (PORT)
import llama_man
from llama_man import PORT # Import PORT for constructing URL

@click.command('chat-message')
@click.option('--prompt', required=True, help='The prompt to send to the server.')
def chat_message_command(prompt):
    """Sends prompt to llama-server, auto-starting if needed. Streams response."""

    # --- Ensure server is running ---
    status_code, message = llama_man.ensure_server_running_or_fail()

    if status_code == "RUNNING":
        click.secho(message, fg='green')
    elif status_code == "FAILED_START":
        click.secho(message, fg='red')
        click.echo("Aborting prompt.")
        sys.exit(1)
    else:
        click.secho(f"Unexpected server status: {status_code} - {message}", fg='yellow')
        click.echo("Aborting prompt.")
        sys.exit(1)
    # --- Server confirmed running ---

    click.echo("Server confirmed running. Sending prompt...")

    # --- Chat Logic using Requests with Streaming ---
    server_url = f"http://127.0.0.1:{PORT}/completion"
    # Add "stream": True to the payload to request streaming
    payload = {"prompt": prompt, "n_predict": -1, "stream": True}
    response = None # Define outside try for potential use in except? Not needed here.

    click.echo(f"Sending request to: {server_url}")
    click.echo("\n--- Response ---")

    try:
        # Make the request with stream=True
        response = requests.post(
            server_url,
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"}, # Added Accept header
            json=payload,
            timeout=90, # Overall timeout still applies
            stream=True # <<<--- Enable streaming
        )
        response.raise_for_status() # Check for initial HTTP errors (4xx, 5xx)

        # Process the stream line by line
        found_content = False
        for line in response.iter_lines():
            if line: # Filter out keep-alive new lines
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data:'):
                    json_data_part = decoded_line[len('data:'):].strip()
                    if json_data_part: # Ensure there's data after "data:"
                        try:
                            data = json.loads(json_data_part)
                            # Check for content chunk and print
                            if isinstance(data, dict) and 'content' in data:
                                chunk = data.get('content', '')
                                if chunk:
                                    click.echo(chunk, nl=False)
                                    found_content = True
                            # Optional: Check for stop signal if server sends one
                            # if isinstance(data, dict) and data.get('stop') == True:
                            #    break

                        except json.JSONDecodeError:
                            # Handle cases where a 'data:' line isn't valid JSON
                            # Could happen if connection interrupted or server sends malformed event
                             click.secho(f"\n[Warning: Could not decode stream chunk: {json_data_part}]", fg='yellow', nl=True)
                             continue # Try processing next line

        if not found_content:
            click.echo("[No content received from stream or stream empty]")

        click.echo() # Final newline after streaming completes

    except requests.exceptions.ConnectionError:
        click.secho(f"\nError: Connection refused at {server_url}.", fg='red')
        click.secho("=> Server might have stopped or is not listening.", fg='yellow')
        sys.exit(1)
    except requests.exceptions.Timeout:
        click.secho(f"\nError: Request timed out connecting to {server_url}.", fg='red')
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        # Handles HTTP errors caught by raise_for_status and other request issues
        click.secho(f"\nError during request to {server_url}: {e}", fg='red')
        if e.response is not None:
            # Try to show raw response if available, even with streaming on error
            try:
                 # Reading response.text might fail if stream=True and error occurred early
                 raw_text = e.response.text
            except Exception:
                 raw_text = "[Could not read error response body]"
            click.secho(f"Server raw response: {raw_text}", fg='red')
        sys.exit(1)
    # Removed specific JSONDecodeError handler here, as it's handled per-chunk in the loop
    except Exception as e:
        # Catch-all for other unexpected errors during request or stream processing
        click.secho(f"\nAn unexpected error occurred: {e}", fg='red')
        sys.exit(1)
    # --- End Chat Logic ---

    click.echo("----------------\n")


# Export the command function directly as 'cli' for main.py
cli = chat_message_command