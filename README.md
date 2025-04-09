- Download the release as a zip file from https://github.com/ggml-org/llama.cpp/releases
- Unzip the file
- Download the model from HuggingFace. One of my favourits is Unsloth https://huggingface.co/unsloth/gemma-3-1b-it-GGUF
- Run llama-server with the model `bin/llama-b5061-bin-macos-x64/llama-server -m model/gemma-3-1b-it-Q4_K_M.gguf --port 8012 -ub 1024 -b 1024 --ctx-size 0 --cache-reuse 256`
- With MacOS, we will encounter the following error: 
- Remove the Quarantine Attribute (More direct, using Terminal) 
  - `xattr -d com.apple.quarantine bin/llama-b5061-bin-macos-x64/llama-server`
  - `xattr -d com.apple.quarantine bin/llama-b5061-bin-macos-x64/libllama.dylib`
  - `xattr -d com.apple.quarantine bin/llama-b5061-bin-macos-x64/libggml.dylib`
  - `xattr -d com.apple.quarantine bin/llama-b5061-bin-macos-x64/libggml-blas.dylib`
  - `xattr -d com.apple.quarantine bin/llama-b5061-bin-macos-x64/libggml-cpu.dylib`
  - `xattr -d com.apple.quarantine bin/llama-b5061-bin-macos-x64/libggml-rpc.dylib`
  - `xattr -d com.apple.quarantine bin/llama-b5061-bin-macos-x64/libggml-base.dylib`
```
xattr: Command to manipulate extended file attributes.
-d: Flag to delete an attribute.
com.apple.quarantine: The specific attribute macOS uses to mark downloaded files for Gatekeeper checks.
```
`uv init`
`uv add click requests litellm`
`uv add pyyaml`


```
my_llama_cli/
├── .venv/                      # Virtual environment managed by uv
├── bin/                        # Example dir for server executable
│   └── llama-b5061-bin-macos-x64/
│       └── llama-server        # llama-server executable (path hardcoded in man_llama.py)
├── model/                      # Example dir for model files
│   └── gemma-3-1b-it-Q4_K_M.gguf # LLM model file (path hardcoded in man_llama.py)
├── tests/                      # Unit tests
│   ├── init.py             # Makes 'tests' a Python package
│   ├── test_pid_llama.py       # Tests for pid_llama.py
│   ├── test_man_llama.py       # Tests for man_llama.py
│   ├── test_chatpoint.py       # Tests for chatpoint.py (Rename from test_sendchat.py) <-- RENAMED TEST
│   └── test_cli.py             # Tests for cli.py
├── .gitignore                  # Standard Git ignore file (Recommended)
├── pid_llama.py                # Module for PID file and process checking logic
├── man_llama.py                # Module for server start/stop/status logic (hardcoded config)
├── chatpoint.py                # Module for chat interaction logic using LiteLLM (hardcoded config/switcher) <-- RENAMED
├── cli_server.py                      # Module defining Click command(s) and orchestration
├── main.py                     # Minimal main application entry point script
├── init.py                 # Makes the root directory a Python package (optional but good practice)
├── pyproject.toml              # Project definition, dependencies for uv/pip
├── README.md                   # Project documentation (this file)
└── .llama_server.pid           # Runtime file storing PID of running server (auto-generated)
```

`uv run main.py`

```bash
uv run main.py --prompt "What is LiteLLM?"
```

# Unit Testing
`uv add --dev pytest pytest-mock`