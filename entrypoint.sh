#!/bin/sh
set -e

echo "[INFO] Starting container entrypoint..."

# --- Environment Variables ---
REDIS_HOST=${NF_NITTER_REDIS_HOST:-${REDIS_HOST}}
REDIS_PORT=${NF_NITTER_REDIS_PORT:-${REDIS_PORT:-6379}}
REDIS_PASSWORD=${NF_NITTER_REDIS_PASSWORD:-${REDIS_PASSWORD:-}}
HOSTNAME=${HOSTNAME:-"localhost"}
CONFIG_FILE="/tmp/nitter.conf"

echo "[INFO] Redis Host: $REDIS_HOST"
echo "[INFO] Writing Nitter configuration to $CONFIG_FILE"

# --- Create Configuration in Writable Directory ---
# Create the nitter.conf file from scratch in /tmp
cat > "$CONFIG_FILE" << EOF
[Server]
hostname = "$HOSTNAME"
address = "0.0.0.0"
port = 8080
https = false
sessionSecret = "secret"

[Cache]
listMinutes = 240
rssMinutes = 10
redisHost = "$REDIS_HOST"
redisPort = $REDIS_PORT
redisPassword = "$REDIS_PASSWORD"
redisConnections = 20
redisMaxConnections = 30
redisUseTLS = true

[Config]
hmacKey = "secret"
enableRSS = true
enableDebug = false
EOF

echo "[INFO] Configuration written successfully."
echo "[INFO] Final Redis Config:"
grep "redis" "$CONFIG_FILE" | grep -v "redisPassword" # Print config for verification, hiding password

# --- Start Nitter with Custom Config Path ---
echo "[INFO] Starting Nitter..."
exec /src/nitter "$CONFIG_FILE"

echo "[ERROR] Failed to execute Nitter. Exiting."
exit 1