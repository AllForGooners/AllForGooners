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

echo "[INFO] Configuring Nitter for direct Redis TLS connection..."

# Set the hostname in nitter.conf
if [ -n "$HOSTNAME" ]; then
    echo "Setting hostname to $HOSTNAME"
    sed -i "s/hostname = \".*\"/hostname = \"$HOSTNAME\"/" /src/nitter.conf
else
    echo "Using default hostname: p01--nitter-scraper--6vvf2kxrg48m.code.run"
    sed -i "s/hostname = \".*\"/hostname = \"p01--nitter-scraper--6vvf2kxrg48m.code.run\"/" /src/nitter.conf
fi

# Configure direct Redis connection with TLS
echo "Setting Redis host to $REDIS_HOST"
sed -i "s/redisHost = \".*\"/redisHost = \"$REDIS_HOST\"/" /src/nitter.conf

echo "Setting Redis port to $REDIS_PORT"
sed -i "s/redisPort = [0-9]*/redisPort = $REDIS_PORT/" /src/nitter.conf

if [ -n "$REDIS_PASSWORD" ]; then
    echo "Setting Redis password"
    sed -i "s/redisPassword = \".*\"/redisPassword = \"$REDIS_PASSWORD\"/" /src/nitter.conf
fi

# Enable TLS for Redis connection
echo "Enabling Redis TLS"
sed -i "s/redisUseTLS = false/redisUseTLS = true/" /src/nitter.conf 2>/dev/null || echo "redisUseTLS = true" >> /src/nitter.conf

# Display the final configuration (without showing the password)
echo "[INFO] Final Redis configuration in nitter.conf:"
grep -E "redisHost|redisPort|redisUseTLS" /src/nitter.conf

# Start Nitter
echo "[INFO] Starting Nitter from /src directory..."
cd /src

# Check if nitter executable exists and is executable
if [ -f "./nitter" ] && [ -x "./nitter" ]; then
    echo "Found Nitter executable at /src/nitter"
    
    # Show final configuration
    echo "[INFO] Final Nitter configuration:"
    echo "  Working directory: $(pwd)"
    echo "  Config file: /src/nitter.conf"
    
    # Check if sessions file exists
    if [ -f "./sessions.jsonl" ]; then
        echo "[sessions] parsing JSONL account sessions file: ./sessions.jsonl"
    else
        echo "[WARNING] No sessions.jsonl file found. Nitter will work but with limitations."
    fi
    
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