#!/bin/sh

set -e

# Ensure required environment variables are set
: "${REDIS_HOST:?REDIS_HOST not set}"
: "${REDIS_PORT:?REDIS_PORT not set}"
: "${REDIS_PASSWORD:?REDIS_PASSWORD not set}"

# Path for the generated stunnel config
STUNNEL_CONFIG_PATH="/tmp/stunnel.conf"

# Generate stunnel.conf from the template
# We use /tmp because the container runs as a non-root user 'nitter' who cannot write to /etc/stunnel
cat /etc/stunnel/stunnel.conf.template | sed \
    -e "s/\${REDIS_HOST}/${REDIS_HOST}/g" \
    -e "s/\${REDIS_PORT}/${REDIS_PORT}/g" \
    > "${STUNNEL_CONFIG_PATH}"

echo "stunnel configuration generated at ${STUNNEL_CONFIG_PATH}"

# Start stunnel in the background
echo "Starting stunnel..."
stunnel "${STUNNEL_CONFIG_PATH}"

# Wait for the local Redis proxy to be available
echo "Waiting for stunnel proxy to be ready..."
until redis-cli -h 127.0.0.1 -p 6379 ping > /dev/null 2>&1; do
  echo "stunnel proxy not ready yet, sleeping for 1 second..."
  sleep 1
done

echo "stunnel proxy is ready."

# Update nitter.conf to use the local stunnel proxy
CONFIG_FILE="/src/nitter.conf"

echo "Configuring Nitter to use Redis via stunnel..."

# Use a temporary file to avoid issues with sed -i
TMP_CONFIG_FILE="/tmp/nitter.conf.tmp"

cp "${CONFIG_FILE}" "${TMP_CONFIG_FILE}"

sed -i "s/^redisHost = .*/redisHost = 127.0.0.1/" "${TMP_CONFIG_FILE}"
sed -i "s/^redisPort = .*/redisPort = 6379/" "${TMP_CONFIG_FILE}"
sed -i "s/^redisPassword = .*/redisPassword = ${REDIS_PASSWORD}/" "${TMP_CONFIG_FILE}"

# Overwrite the original config file
mv "${TMP_CONFIG_FILE}" "${CONFIG_FILE}"

echo "nitter.conf updated successfully."

# Start the Nitter application
echo "Starting Nitter..."
exec /src/nitter

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Environment Variable Check ---
# This script requires the external Redis host and port to be set.
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
  echo "Error: REDIS_HOST and REDIS_PORT environment variables must be set."
  exit 1
fi

# --- Configure and Start stunnel ---
# This section creates the stunnel config from a template and starts it.
# stunnel will create a secure TLS tunnel to the real Redis server,
# allowing the insecure Nitter app to connect to it via a simple local port.

echo "Configuring stunnel to bridge 127.0.0.1:6379 -> $REDIS_HOST:$REDIS_PORT..."

# Use sed to replace placeholders in the template and create the final config.
# The config file is written to /tmp, which is writable by any user.
sed -e "s/__REDIS_HOST__/$REDIS_HOST/" \
    -e "s/__REDIS_PORT__/$REDIS_PORT/" \
    /src/stunnel.conf.template > /tmp/stunnel.conf

# Start the stunnel proxy in the background, pointing to our temp config file.
stunnel /tmp/stunnel.conf
echo "stunnel started in background."

# --- Wait for Local Redis Proxy ---
# The script now waits for our LOCAL stunnel proxy to be ready.
# We connect to 127.0.0.1 and provide the password through the tunnel.
echo "Waiting for local Redis proxy (stunnel) to become available..."
CLI_ARGS="-h 127.0.0.1 -p 6379"
if [ -n "$REDIS_PASSWORD" ]; then
  # The password is for Redis authentication, sent through the TLS tunnel.
  CLI_ARGS="$CLI_ARGS -a $REDIS_PASSWORD"
fi

# Loop until our local proxy successfully connects to the real Redis.
until redis-cli $CLI_ARGS ping | grep -q 'PONG'; do
  echo "Waiting for local stunnel proxy and Redis... Retrying..."
  sleep 2
done
echo "Local Redis proxy is available. Proceeding with Nitter configuration."

# --- Configure Nitter ---
CONFIG_FILE="/src/nitter.conf"

# Update Hostname if provided.
if [ -n "$NITTER_HOSTNAME" ]; then
  HOSTNAME_NO_PROTO=${NITTER_HOSTNAME#*//}
  echo "Updating hostname to $HOSTNAME_NO_PROTO"
  sed -i "s|hostname = \".*\"|hostname = \"$HOSTNAME_NO_PROTO\"|" "$CONFIG_FILE"
else
  echo "Warning: NITTER_HOSTNAME environment variable not set."
fi

# Update Redis Configuration to point Nitter to the local stunnel proxy.
echo "Configuring Nitter to use local Redis proxy at 127.0.0.1:6379..."

# Remove any existing Redis config to ensure a clean slate.
sed -i '/redisHost/d' "$CONFIG_FILE"
sed -i '/redisPort/d' "$CONFIG_FILE"
sed -i '/redisPassword/d' "$CONFIG_FILE"
sed -i '/redisUrl/d' "$CONFIG_FILE"

# Add the new configuration pointing to the local proxy.
# Nitter will connect insecurely to stunnel; stunnel secures the connection.
CONFIG_STRING="redisHost = \"127.0.0.1\"\nredisPort = 6379"
if [ -n "$REDIS_PASSWORD" ]; then
  CONFIG_STRING="$CONFIG_STRING\nredisPassword = \"$REDIS_PASSWORD\""
fi

# Insert the Redis configuration into nitter.conf under the [Cache] section.
awk -v config="$CONFIG_STRING" '/\[Cache\]/ {print; print config; next} 1' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
echo "Nitter configured to use Redis via stunnel."

# --- Start Nitter ---
# Finally, execute the main Nitter binary.
# 'exec' replaces the shell process, making Nitter the main container process.
echo "Starting Nitter..."
exec /src/nitter
