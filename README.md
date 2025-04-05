- Download the release as a zip file from https://github.com/ggml-org/llama.cpp/releases
- Unzip the file
- Download the model from HuggingFace. One of my favourits is Unsloth https://huggingface.co/unsloth
- Run llama-server with the model `bin/llama-b5054-bin-macos-x64/llama-server -m model/gemma-3-1b-it-Q4_K_M.gguf --port 8012 -ub 1024 -b 1024 --ctx-size 0 --cache-reuse 256`
- With MacOS, we will encounter the following error: 
- Remove the Quarantine Attribute (More direct, using Terminal) `xattr -d com.apple.quarantine bin/llama-b5054-bin-macos-x64/llama-server`
```
xattr: Command to manipulate extended file attributes.
-d: Flag to delete an attribute.
com.apple.quarantine: The specific attribute macOS uses to mark downloaded files for Gatekeeper checks.
```
- 
 