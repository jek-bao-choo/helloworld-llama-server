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
`uv add click requests`


```
my_llama_cli/
├── .venv/                 # Your virtual environment (managed by uv)
├── bin/
│   └── llama-b5061-bin-macos-x64/
│       └── llama-server   # Your server executable
├── model/
│   └── gemma-3-1b-it-Q4_K_M.gguf # Your model file
├── main.py                # New main entry point
├── cli.py                 # Click commands logic
├── util.py                # Helper functions and config
├── pyproject.toml         # Project definition
└── .llama_server.pid      # Created/deleted by the script
```

`uv run main.py`

```bash
uv run main.py send-prompt --prompt "Explain quantum physics simply."
```