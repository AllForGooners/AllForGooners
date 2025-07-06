#!/bin/sh
set -e

echo "[INFO] Starting container entrypoint..."

# Function to safely get environment variables
get_env_var() {
    local var_name="$1"
    local default_value="$2"
    
    # Try NF_NITTER_ prefixed version first, then regular version, then default
    eval "local nf_value=\$NF_NITTER_${var_name}"
    eval "local regular_value=\$${var_name}"
    
    if [ -n "$nf_value" ]; then
        echo "$nf_value"
    elif [ -n "$regular_value" ]; then
        echo "$regular_value"
    else
        echo "$default_value"
    fi
}

echo "[INFO] Securely fetching environment variables..."

# Get Redis configuration - use explicit environment variables
REDIS_HOST=${NF_NITTER_REDIS_HOST:-${REDIS_HOST:-master.nitter-redis--6vvf2kxrg48m.addon.code.run}}
REDIS_PORT=${NF_NITTER_REDIS_PORT:-${REDIS_PORT:-6379}}
REDIS_PASSWORD=${NF_NITTER_REDIS_PASSWORD:-${REDIS_PASSWORD:-}}

echo "[INFO] Redis configuration:"
echo "  Host: $REDIS_HOST"
echo "  Port: $REDIS_PORT"
echo "  Password: $(if [ -n "$REDIS_PASSWORD" ]; then echo "Set"; else echo "Not set"; fi)"

# Create a directory where we have write permissions
mkdir -p /tmp/stunnel

# Try direct Redis connection first to verify connectivity
echo "[INFO] Testing direct Redis connection..."
if command -v redis-cli >/dev/null 2>&1; then
    if [ -n "$REDIS_PASSWORD" ]; then
        # Try with password
        REDIS_RESULT=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping 2>&1) || echo "Failed"
    else
        # Try without password
        REDIS_RESULT=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>&1) || echo "Failed"
    fi
    
    echo "Direct Redis connection test result: $REDIS_RESULT"
    
    # Check if TLS is required
    if echo "$REDIS_RESULT" | grep -q "NOAUTH\|wrong number of arguments\|ERR"; then
        echo "[INFO] Redis authentication failed, trying with TLS..."
        if [ -n "$REDIS_PASSWORD" ]; then
            REDIS_TLS_RESULT=$(redis-cli --tls -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping 2>&1) || echo "Failed"
        else
            REDIS_TLS_RESULT=$(redis-cli --tls -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>&1) || echo "Failed"
        fi
        echo "Direct Redis TLS connection test result: $REDIS_TLS_RESULT"
    fi
else
    echo "[WARNING] redis-cli not found, skipping direct connection test"
fi

# Try to resolve the Redis host
echo "[INFO] Resolving Redis host: $REDIS_HOST"
getent hosts "$REDIS_HOST" || echo "Failed to resolve host"

# Create stunnel configuration in /tmp where we have write permissions
cat << EOF > /tmp/stunnel/stunnel.conf
pid = /tmp/stunnel/stunnel.pid
foreground = no
debug = 7
output = /tmp/stunnel/stunnel.log

[redis-tls]
client = yes
accept = 127.0.0.1:6379
connect = ${REDIS_HOST}:${REDIS_PORT}
# Security settings required by newer stunnel versions
verifyChain = yes
verifyPeer = yes
# But make it insecure since we don't have proper certs
checkHost = no
CAfile = /etc/ssl/certs/ca-certificates.crt
insecure = yes  # Allow insecure connections despite verification
sslVersion = TLSv1.2
EOF

echo "[INFO] Starting stunnel with config:"
cat /tmp/stunnel/stunnel.conf

# Start stunnel with our custom config
stunnel /tmp/stunnel/stunnel.conf

# Give stunnel a moment to start
sleep 2

# Check if stunnel is running
echo "[INFO] Checking if stunnel is running:"
ps aux | grep stunnel || echo "No stunnel process found"

# Check if the local port is listening
echo "[INFO] Checking if local port is open:"
netstat -tulpn | grep 6379 || echo "Port 6379 is not open"

# Check stunnel log if it exists
if [ -f "/tmp/stunnel/stunnel.log" ]; then
    echo "[INFO] Stunnel log content:"
    cat /tmp/stunnel/stunnel.log
else
    echo "[WARNING] No stunnel log file found"
fi

# Since we're having issues with stunnel, let's try a direct connection approach
echo "[INFO] Attempting direct Redis connection in nitter.conf..."

# The rest of the script will connect directly to Redis
echo "[INFO] Configuring Nitter for direct Redis connection..."

# Set the hostname in nitter.conf
if [ -n "$HOSTNAME" ]; then
    echo "Setting hostname to $HOSTNAME"
    sed -i "s/hostname = \".*\"/hostname = \"$HOSTNAME\"/" /src/nitter.conf
else
    echo "Using default hostname: p01--nitter-scraper--6vvf2kxrg48m.code.run"
    sed -i "s/hostname = \".*\"/hostname = \"p01--nitter-scraper--6vvf2kxrg48m.code.run\"/" /src/nitter.conf
fi

# Configure direct Redis connection
echo "Setting Redis host to $REDIS_HOST"
sed -i "s/redisHost = \".*\"/redisHost = \"$REDIS_HOST\"/" /src/nitter.conf

echo "Setting Redis port to $REDIS_PORT"
sed -i "s/redisPort = [0-9]*/redisPort = $REDIS_PORT/" /src/nitter.conf

if [ -n "$REDIS_PASSWORD" ]; then
    echo "Setting Redis password"
    sed -i "s/redisPassword = \".*\"/redisPassword = \"$REDIS_PASSWORD\"/" /src/nitter.conf
fi

# Try to enable TLS for Redis connection
echo "Enabling Redis TLS"
sed -i "s/redisUseTLS = false/redisUseTLS = true/" /src/nitter.conf 2>/dev/null || echo "redisUseTLS = true" >> /src/nitter.conf

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
    echo "  Redis host: $REDIS_HOST"
    echo "  Redis port: $REDIS_PORT"
    
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