# config_loader.py
import yaml # Requires PyYAML dependency
import os
import sys

CONFIG_FILENAME = 'llama_config.yaml'

def load_config():
    """Loads configuration from CONFIG_FILENAME using PyYAML."""
    if not os.path.exists(CONFIG_FILENAME):
        print(f"Error: Configuration file '{CONFIG_FILENAME}' not found in {os.getcwd()}", file=sys.stderr)
        sys.exit(f"Configuration file '{CONFIG_FILENAME}' not found.")

    try:
        with open(CONFIG_FILENAME, 'r') as f:
            # Use safe_load to prevent arbitrary code execution from malicious YAML
            config_data = yaml.safe_load(f)
            if config_data is None:
                 print(f"Warning: Configuration file '{CONFIG_FILENAME}' is empty or invalid.", file=sys.stderr)
                 return {} # Return empty dict to handle gracefully downstream if possible
            return config_data
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file '{CONFIG_FILENAME}': {e}", file=sys.stderr)
        sys.exit(f"Error parsing YAML configuration file: {e}")
    except IOError as e:
        print(f"Error reading configuration file '{CONFIG_FILENAME}': {e}", file=sys.stderr)
        sys.exit(f"Error reading configuration file: {e}")

def _get_nested_dict(config_data, section_name):
    """Safely gets a nested dictionary section, exiting if missing/invalid."""
    section = config_data.get(section_name) if isinstance(config_data, dict) else None
    if not isinstance(section, dict):
        print(f"Error: Missing or invalid section '{section_name}' in {CONFIG_FILENAME}", file=sys.stderr)
        sys.exit(f"Missing or invalid section '{section_name}' in config file.")
    return section

def get_llama_config(config_data):
    """Extracts llama_server configuration from loaded YAML data."""
    section = _get_nested_dict(config_data, 'llama_server')

    # Use .get() for safe access, provide defaults. PyYAML handles type conversion.
    port = section.get('port', 8012)
    if not isinstance(port, int):
        print(f"Error: 'port' in [llama_server] must be an integer.", file=sys.stderr); sys.exit(1)

    # Check required paths
    server_path = section.get('server_path')
    model_path = section.get('model_path')
    if not server_path:
        print(f"Error: 'server_path' missing in [llama_server] section of {CONFIG_FILENAME}", file=sys.stderr); sys.exit(1)
    if not model_path:
        print(f"Error: 'model_path' missing in [llama_server] section of {CONFIG_FILENAME}", file=sys.stderr); sys.exit(1)

    return {
        'server_path': server_path,
        'model_path': model_path,
        'port': port,
        'ctx_size': section.get('ctx_size', 0),
        'batch_size': section.get('batch_size', 1024),
        'ub': section.get('ub', 1024),
        'cache_reuse': section.get('cache_reuse', 256),
    }

def get_chat_config(config_data, llama_config): # Pass llama_config to get dependent port
    """Extracts chat configuration from loaded YAML data."""
    section = _get_nested_dict(config_data, 'chat')

    llama_port = llama_config.get('port', 8012) # Get port from already processed llama_config
    default_api_base = f"http://127.0.0.1:{llama_port}/v1"
    default_model = "default-model"

    return {
        'api_base': section.get('api_base_url', default_api_base),
        'model_string': section.get('model_string', default_model),
        'api_key': section.get('api_key', 'dummy-key')
    }

# --- Load Config on Import ---
# Performs loading and validation once when any module imports this.
try:
    _loaded_config_data = load_config()
    LLAMA_CONFIG = get_llama_config(_loaded_config_data)
    CHAT_CONFIG = get_chat_config(_loaded_config_data, LLAMA_CONFIG)
except SystemExit:
    # Prevent continuation if config loading failed and exited
    print("Exiting due to configuration errors.", file=sys.stderr)
    raise # Re-raise to ensure script stops
except Exception as e:
    # Catch any other unexpected error during initial config processing
    print(f"Fatal Error during configuration loading: {e}", file=sys.stderr)
    sys.exit(1)
# --- End Load Config on Import ---