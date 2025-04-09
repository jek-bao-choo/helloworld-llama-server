# cli.py
import click
import time
import sys
import man_llama
import chatpoint

def _ensure_server_running_or_fail():
    """Checks server status, starts if needed. Returns True if running, False on failure."""
    # This function now relies on man_llama using its internal hardcoded config
    status_code, message = man_llama.status_llama_server()
    click.echo(f"Initial server status: {status_code} - {message}")

    if status_code == "RUNNING":
        return True

    click.echo("Server not running. Attempting auto-start with internal defaults...")
    # start_llama_server now uses hardcoded defaults internally
    success, start_message, pid = man_llama.start_llama_server()

    if success:
        click.secho(f"Auto-start successful: {start_message}", fg='green')
        time.sleep(2.5) # Give server time to initialize
        return True
    else:
        click.secho(f"Auto-start failed: {start_message}", fg='red')
        return False


@click.command('chat-message')
@click.option('--prompt', required=True, help='The prompt to send to the server.')
def chat_message_command(prompt):
    """Sends prompt to llama-server, auto-starting if needed. Streams response."""

    if not _ensure_server_running_or_fail():
        sys.exit(1)

    click.echo("Server confirmed running. Sending prompt...")
    click.echo("\n--- Response ---")

    try:
        # send_prompt now uses hardcoded defaults internally
        stream = chat_llama.send_prompt(prompt=prompt)
        found_content = False
        for chunk in stream:
             if chunk:
                 click.echo(chunk, nl=False)
                 found_content = True

        if not found_content:
             click.echo("\n[No content received from stream]")

        click.echo() # Final newline
        click.echo("----------------\n")

    except Exception as e:
        click.secho(f"\nAn error occurred processing the chat response: {e}", fg='red')
        sys.exit(1)

# Export the command function directly as 'cli' for main.py
cli = chat_message_command