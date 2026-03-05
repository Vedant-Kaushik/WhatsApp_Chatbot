#!/bin/bash
echo "===== Application Startup at $(date '+%Y-%m-%d %H:%M:%S') ====="

# Bypass DNS for graph.facebook.com by adding static host entry
# (DNS can't resolve it on HF, but we can hardcode the IP)
echo "Attempting /etc/hosts workaround for graph.facebook.com..."
python3 -c "
import socket
# First, try if DNS already works
try:
    ip = socket.gethostbyname('graph.facebook.com')
    print(f'  DNS works: graph.facebook.com -> {ip}')
except:
    # DNS fails, try writing to /etc/hosts
    import subprocess
    # Get IP from a working DNS-over-HTTPS service
    try:
        import urllib.request, json
        resp = urllib.request.urlopen('https://dns.google/resolve?name=graph.facebook.com&type=A', timeout=5)
        data = json.loads(resp.read())
        ip = data['Answer'][0]['data']
        with open('/etc/hosts', 'a') as f:
            f.write(f'{ip} graph.facebook.com\n')
        print(f'  ✅ Added {ip} graph.facebook.com to /etc/hosts')
    except PermissionError:
        print('  ❌ /etc/hosts is also read-only. WhatsApp bot cannot work on this platform.')
    except Exception as e:
        print(f'  ❌ Workaround failed: {e}')

# Verify final state
try:
    ip = socket.gethostbyname('graph.facebook.com')
    print(f'  ✅ Final check: graph.facebook.com -> {ip}')
except Exception as e:
    print(f'  ❌ Final check: {e}')
"

exec uv run uvicorn main:app --host 0.0.0.0 --port 7860
