# chatpoint.py
import litellm
import sys

# --- Hardcoded Configuration ---
# Should match the port used in man_llama.py
LLAMA_PORT = 8012
# Ensure API Base includes /v1 if required by llama-server's OpenAI endpoint
API_BASE = f"http://127.0.0.1:{LLAMA_PORT}/v1"
# Model string - adjust if needed for litellm/server
MODEL_STRING = "openai/gemma-3-1b-it-Q4_K_M.gguf" # Keep openai/ prefix for litellm
API_KEY = "dummy-key"
# --- End Hardcoded Configuration ---

def send_prompt(prompt: str):
    """
    Sends prompt to configured server using litellm SDK and yields response chunks.
    Uses hardcoded configuration constants.

    Args:
        prompt: The user's prompt string.

    Yields:
        Content chunks (str) from the streaming response.
    """
    # Use constants defined above
    api_base = API_BASE
    model_name = MODEL_STRING
    api_key = API_KEY

    messages = [{"role": "user", "content": prompt}]

    try:
        litellm.drop_params=True
        stream = litellm.completion(
            model=model_name,
            messages=messages,
            api_base=api_base,
            api_key=api_key,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta:
                 content = chunk.choices[0].delta.content
                 if content:
                     yield content

    except litellm.exceptions.APIConnectionError as e:
        print(f"\nError [LiteLLM]: Cannot connect to API Base '{api_base}'.", file=sys.stderr)
        print(f"   Check if the server is running and constants (PORT) are correct.", file=sys.stderr)
        print(f"   Details: {e}", file=sys.stderr)
        return
    except litellm.exceptions.APIError as e:
         print(f"\nError [LiteLLM]: API Error from server '{api_base}'. Status: {e.status_code}", file=sys.stderr)
         print(f"   Details: {e}", file=sys.stderr)
         return
    except Exception as e:
        print(f"\nAn unexpected error occurred during LiteLLM chat streaming: {e}", file=sys.stderr)
        return