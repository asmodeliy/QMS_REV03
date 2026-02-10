#!/bin/bash

echo "=== Changing to TinyLlama (Fast Model) ==="

MODEL_DIR="/home/ronnie/LLM/models"
MODEL_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/TinyLlama-1.1B-Chat-v1.0.Q5_K_M.gguf"
MODEL_FILE="$MODEL_DIR/TinyLlama-1.1B-Chat-v1.0.Q5_K_M.gguf"

echo "📦 Downloading TinyLlama (560MB)..."
cd "$MODEL_DIR"
wget -q --show-progress "$MODEL_URL" -O "$MODEL_FILE"

if [ -f "$MODEL_FILE" ]; then
    echo "✅ Download complete!"
    echo ""
    echo "📋 Update gpt4all_routes.py with:"
    echo '  model_name = "TinyLlama-1.1B-Chat-v1.0.Q5_K_M"'
    echo ""
    echo "Then restart server:"
    echo "  pkill -f uvicorn"
    echo "  cd ~/ADD_LLM && nohup uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 > server.log 2>&1 &"
else
    echo "❌ Download failed!"
fi
