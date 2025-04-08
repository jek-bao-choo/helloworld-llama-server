# cli.py
import click
import time
import sys

# Import necessary functions from other modules
import man_llama
import chat_llama
import config_loader # To potentially check if config loaded okay, though it exits on fail now


def _ensure_server_running_or_fail():
    """Checks server status, starts if needed. Returns True if running, False on failure."""
    status_code, message = man_llama.status_llama_server()
    click.echo(f"Initial server status: {status_code} - {message}") # Inform user

    if status_code == "RUNNING":
        return True

    # Attempt to start if STOPPED or STALE_PID
    click.echo("Server not running. Attempting auto-start...")
    success, start_message, pid = man_llama.start_llama_server() # Uses config internally

    if success:
        click.secho(f"Auto-start successful: {start_message}", fg='green')
        # Short pause after starting before trying to connect
        time.sleep(2.5)
        return True
    else:
        click.secho(f"Auto-start failed: {start_message}", fg='red')
        return False


@click.command('chat-message')
@click.option('--prompt', required=True, help='The prompt to send to the server.')
def chat_message_command(prompt):
    """Sends prompt to llama-server, auto-starting if needed. Streams response."""

    # Ensure server is running or exit
    if not _ensure_server_running_or_fail():
        sys.exit(1) # Exit with error code if server couldn't be started

    click.echo("Server confirmed running. Sending prompt...")
    click.echo("\n--- Response ---")

    try:
        # Get the stream generator
        stream = chat_llama.send_prompt(prompt=prompt)
        found_content = False
        # Print chunks as they arrive
        for chunk in stream:
             if chunk:
                 click.echo(chunk, nl=False)
                 found_content = True

        if not found_content:
             # Handle cases where stream completed but yielded nothing (maybe an error printed in chat_llama)
             click.echo("\n[No content received from stream]")

        click.echo() # Final newline after streaming completes
        click.echo("----------------\n")

    except Exception as e:
        # Catch unexpected errors during stream iteration if any occur
        click.secho(f"\nAn error occurred processing the chat response: {e}", fg='red')
        sys.exit(1)


# Export the command function directly as 'cli' for main.py
cli = chat_message_command