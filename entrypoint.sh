#!/bin/sh
set -e

echo "[INFO] Starting container entrypoint..."

# Get Redis configuration - use explicit environment variables
REDIS_HOST=${NF_NITTER_REDIS_HOST:-${REDIS_HOST:-master.nitter-redis--6vvf2kxrg48m.addon.code.run}}
REDIS_PORT=${NF_NITTER_REDIS_PORT:-${REDIS_PORT:-6379}}
REDIS_PASSWORD=${NF_NITTER_REDIS_PASSWORD:-${REDIS_PASSWORD:-}}

echo "[INFO] Redis configuration:"
echo "  Host: $REDIS_HOST"
echo "  Port: $REDIS_PORT"
echo "  Password: $(if [ -n "$REDIS_PASSWORD" ]; then echo "Set"; else echo "Not set"; fi)"

# Try to resolve the Redis host
echo "[INFO] Resolving Redis host: $REDIS_HOST"
getent hosts "$REDIS_HOST" || echo "Failed to resolve host"

echo "[INFO] Creating a clean nitter.conf file..."

# Create a completely new nitter.conf file instead of modifying the existing one
cat > /src/nitter.conf << EOF
[Server]
hostname = "p01--nitter-scraper--6vvf2kxrg48m.code.run"
title = "nitter"
address = "0.0.0.0"
port = 8080
https = false
httpMaxConnections = 100
staticDir = "./public"
sessionSecret = "nitter"

[Cache]
listMinutes = 240
rssMinutes = 10
redisHost = "${REDIS_HOST}"
redisPort = ${REDIS_PORT}
redisPassword = "${REDIS_PASSWORD}"
redisConnections = 20
redisMaxConnections = 30
redisUseTLS = true

[Config]
hmacKey = "nitter"
base64Media = false
enableRSS = true
enableDebug = true
proxy = ""
proxyAuth = ""
tokenCount = 10
EOF

echo "[INFO] Created new nitter.conf:"
cat /src/nitter.conf | grep -v "redisPassword"

# Verify sessions.jsonl file
echo "[INFO] Checking sessions.jsonl file..."
if [ -f "/src/sessions.jsonl" ]; then
    # Make sure the file is valid JSON Lines format
    echo "[INFO] Recreating sessions.jsonl with valid format"
    echo '{"username":"placeholder","cookies":{"ct0":"placeholder_token","auth_token":"placeholder_auth_token"},"guest":true,"lastUsed":1720000000000}' > /src/sessions.jsonl
    echo "[INFO] sessions.jsonl content:"
    cat /src/sessions.jsonl
else
    echo "[INFO] Creating sessions.jsonl file"
    echo '{"username":"placeholder","cookies":{"ct0":"placeholder_token","auth_token":"placeholder_auth_token"},"guest":true,"lastUsed":1720000000000}' > /src/sessions.jsonl
fi

# Start Nitter
echo "[INFO] Starting Nitter from /src directory..."
cd /src

# Check if nitter executable exists and is executable
if [ -f "./nitter" ] && [ -x "./nitter" ]; then
    echo "[INFO] Found Nitter executable at /src/nitter"
    
    echo "[INFO] Starting Nitter..."
    exec ./nitter
else
    echo "[ERROR] Could not find Nitter executable at /src/nitter"
    
    # Enhanced fallback search
    echo "[INFO] Searching for nitter executable in common locations..."
    NITTER_PATHS="/app/nitter /nitter /usr/local/bin/nitter /usr/bin/nitter"
    
    for path in $NITTER_PATHS; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            echo "[SUCCESS] Found Nitter executable at $path"
            cd "$(dirname "$path")"
            exec "./$(basename "$path")"
            exit 0
        fi
    done
    
    # If we get here, we couldn't find the executable
    echo "[ERROR] Could not find Nitter executable. Searched common locations."
    echo "[DEBUG] Listing files in /src directory:"
    ls -la /src
    
    exit 1
fi