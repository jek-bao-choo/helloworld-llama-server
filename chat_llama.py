# chat_llama.py
import litellm  # Import litellm instead of openai
import sys
from config_loader import CHAT_CONFIG # Keep importing loaded config

# Optional: Configure litellm verbosity/logging if desired for debugging
# litellm.set_verbose = False
# litellm.success_callback = []
# litellm.failure_callback = []

def send_prompt(prompt: str):
    """
    Sends prompt to configured server using litellm SDK and yields response chunks.

    Args:
        prompt: The user's prompt string.

    Yields:
        Content chunks (str) from the streaming response.
        Returns None or stops yielding upon error.
    """
    cfg = CHAT_CONFIG
    api_base = cfg['api_base']
    model_name = cfg['model_string']
    api_key = cfg['api_key'] # litellm uses this parameter name

    messages = [{"role": "user", "content": prompt}]

    try:
        # Ensure litellm doesn't add unexpected params for custom servers
        # Good practice when pointing litellm to non-standard endpoints
        litellm.drop_params=True

        # Call litellm.completion with stream=True
        stream = litellm.completion(
            model=model_name,
            messages=messages,
            api_base=api_base,
            api_key=api_key, # Pass the API key
            stream=True,
            # You can add other compatible parameters here, e.g.
            # temperature=0.7,
            # max_tokens=1000, # Optional: litellm can pass this if server supports it
        )

        # Yield content chunks from the stream
        # LiteLLM's streaming chunks generally mimic the OpenAI structure
        for chunk in stream:
            # Check structure carefully based on observed chunks if needed
            if chunk.choices and chunk.choices[0].delta:
                 content = chunk.choices[0].delta.content
                 if content: # Ensure content is not None or empty
                     yield content
            # You could add checks here for finish_reason if needed

    except litellm.exceptions.APIConnectionError as e:
        # Handle litellm's specific connection error
        # Use sys.stderr to avoid interfering with potential stdout piping
        print(f"\nError [LiteLLM]: Cannot connect to API Base '{api_base}'.", file=sys.stderr)
        print(f"   Check if the server is running and the URL in config.yaml is correct.", file=sys.stderr)
        print(f"   Details: {e}", file=sys.stderr)
        return # Stop yielding gracefully
    except litellm.exceptions.APIError as e:
         # Handle other API errors reported by litellm (e.g., bad request, auth)
         print(f"\nError [LiteLLM]: API Error from server '{api_base}'. Status: {e.status_code}", file=sys.stderr)
         print(f"   Details: {e}", file=sys.stderr)
         return
    except Exception as e:
        # Catch any other unexpected errors during the litellm call or stream iteration
        print(f"\nAn unexpected error occurred during LiteLLM chat streaming: {e}", file=sys.stderr)
        print(f"   Prompt: '{prompt}'", file=sys.stderr)
        return # Stop yielding