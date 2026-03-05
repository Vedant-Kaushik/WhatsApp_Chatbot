#!/bin/bash
echo "===== Application Startup at $(date '+%Y-%m-%d %H:%M:%S') ====="

# DNS diagnostic - let's find out what's actually happening
echo "Testing DNS resolution..."
python3 -c "
import socket
for host in ['graph.facebook.com', 'api.upstox.com', 'ep-long-cell-a1tdq7ys-pooler.ap-southeast-1.aws.neon.tech']:
    try:
        ip = socket.gethostbyname(host)
        print(f'  ✅ {host} -> {ip}')
    except Exception as e:
        print(f'  ❌ {host} -> {e}')
"

exec uv run uvicorn main:app --host 0.0.0.0 --port 7860
