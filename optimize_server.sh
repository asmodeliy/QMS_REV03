#!/bin/bash

echo "=== QMS Server Performance Optimization ==="
echo ""

# 1. Kill existing uvicorn processes
echo "1️⃣  Stopping all uvicorn processes..."
pkill -f "uvicorn app:app"
sleep 3

echo "2️⃣  Clearing Python cache..."
find ~/ADD_LLM -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

echo "3️⃣  Starting uvicorn in PRODUCTION mode..."
cd ~/ADD_LLM

# Production settings:
# - NO --reload (development mode disabled)
# - Single worker
# - Direct localhost only
# - Workers=1 to avoid multiprocessing overhead
nohup uvicorn app:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --log-level info \
  > server.log 2>&1 &

sleep 2

echo "4️⃣  Verifying server..."
ps aux | grep -E "uvicorn|python3.11.*spawn" | grep -v grep | wc -l

echo ""
echo "5️⃣  Testing endpoint..."
sleep 3
curl -X POST http://127.0.0.1:8000/gpt4all/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "hi"}' \
  -s | head -c 200

echo ""
echo ""
echo "✅ Server optimization complete!"
echo ""
echo "📋 Performance improvements:"
echo "   - Removed --reload (development mode disabled)"
echo "   - Single worker (no multiprocessing overhead)"
echo "   - Production runserver settings"
echo "   - Cleaned __pycache__"
echo ""
echo "📊 Monitor with: tail -f ~/ADD_LLM/server.log"
