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

# Get Redis configuration for stunnel to connect to the real Redis instance
# First try the prefixed versions, then Redis add-on native names, then defaults
export REDIS_HOST=${NF_NITTER_REDIS_HOST:-${REDIS_HOST:-${HOST:-localhost}}}
export REDIS_PORT=${NF_NITTER_REDIS_PORT:-${REDIS_PORT:-${PORT:-6379}}}
export REDIS_PASSWORD=${NF_NITTER_REDIS_PASSWORD:-${REDIS_PASSWORD:-${PASSWORD:-}}}

echo "[INFO] Starting stunnel for secure Redis connection..."
# Start stunnel in the background
stunnel /etc/stunnel/stunnel.conf

# The rest of the script will connect to the local stunnel proxy
echo "[INFO] Pointing Nitter to local stunnel proxy at 127.0.0.1:6379"
REDIS_HOST_VAR="127.0.0.1"
REDIS_PORT_VAR="6379"
# The connection to the local proxy does not require a password, as stunnel handles authentication.
REDIS_PASSWORD_VAR=""

echo "[INFO] Configuring Nitter for Northflank deployment..."

# Set the hostname in nitter.conf
if [ -n "$HOSTNAME" ]; then
    echo "Setting hostname to $HOSTNAME"
    sed -i "s/hostname = \".*\"/hostname = \"$HOSTNAME\"/" /src/nitter.conf
else
    echo "Using default hostname: p01--nitter-scraper--6vvf2kxrg48m.code.run"
    sed -i "s/hostname = \".*\"/hostname = \"p01--nitter-scraper--6vvf2kxrg48m.code.run\"/" /src/nitter.conf
fi

echo "Setting Redis host to $REDIS_HOST_VAR"
sed -i "s/redisHost = \".*\"/redisHost = \"$REDIS_HOST_VAR\"/" /src/nitter.conf

echo "Setting Redis port to $REDIS_PORT_VAR"
sed -i "s/redisPort = [0-9]*/redisPort = $REDIS_PORT_VAR/" /src/nitter.conf

if [ -n "$REDIS_PASSWORD_VAR" ] && [ "$REDIS_PASSWORD_VAR" != "" ]; then
    echo "Setting Redis password"
    sed -i "s/redisPassword = \".*\"/redisPassword = \"$REDIS_PASSWORD_VAR\"/" /src/nitter.conf
fi

# Enhanced Redis connection testing
echo "[INFO] Testing Redis connection..."
MAX_RETRIES=60  # Increased from 30 to 60
RETRY_INTERVAL=3  # Increased from 2 to 3 seconds
RETRIES=0

# Function to test Redis connection
test_redis_connection() {
    # Test without password, as stunnel handles authentication for the local proxy.
    redis-cli -h "$REDIS_HOST_VAR" -p "$REDIS_PORT_VAR" ping 2>/dev/null
}

echo "Waiting for Redis to be ready at $REDIS_HOST_VAR:$REDIS_PORT_VAR..."

while [ $RETRIES -lt $MAX_RETRIES ]; do
    if test_redis_connection | grep -q "PONG"; then
        echo "[SUCCESS] Redis is ready!"
        break
    else
        echo "[RETRY $((RETRIES+1))/$MAX_RETRIES] Redis not ready yet, retrying in $RETRY_INTERVAL seconds..."
        
        # Show more debug info every 10 retries
        if [ $((RETRIES % 10)) -eq 0 ] && [ $RETRIES -gt 0 ]; then
            echo "[DEBUG] Checking if Redis host is reachable..."
            if command -v nc >/dev/null 2>&1; then
                nc -z "$REDIS_HOST_VAR" "$REDIS_PORT_VAR" 2>/dev/null && echo "[DEBUG] Port is open" || echo "[DEBUG] Port is not reachable"
            fi
            if command -v nslookup >/dev/null 2>&1; then
                echo "[DEBUG] DNS lookup for $REDIS_HOST_VAR:"
                nslookup "$REDIS_HOST_VAR" 2>/dev/null | head -5 || echo "[DEBUG] DNS lookup failed"
            fi
        fi
        
        sleep $RETRY_INTERVAL
        RETRIES=$((RETRIES+1))
    fi
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
    echo "[ERROR] Redis is not available after $MAX_RETRIES retries."
    echo "[ERROR] Redis configuration:"
    echo "  Host: $REDIS_HOST_VAR"
    echo "  Port: $REDIS_PORT_VAR"
    echo "  Password: $([ -n "$REDIS_PASSWORD_VAR" ] && echo "Set" || echo "Not set")"
    echo "[ERROR] Continuing anyway, but Nitter might not work properly."
fi

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
    echo "  Redis host: $REDIS_HOST_VAR"
    echo "  Redis port: $REDIS_PORT_VAR"
    
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
    
    echo "[DEBUG] Searching for nitter executable in the filesystem..."
    find / -name "nitter" -type f -executable 2>/dev/null || echo "[DEBUG] No nitter executable found."
    
    exit 1
fi