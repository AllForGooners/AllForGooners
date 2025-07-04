#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# This script requires REDIS_HOST and REDIS_PORT to be set for cloud deployment.
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
  echo "Error: REDIS_HOST and REDIS_PORT environment variables must be set."
  exit 1
fi

# Define the path to the config file
CONFIG_FILE="/src/nitter.conf"

# --- Wait for Redis ---
# Build the redis-cli command with an optional password.
CLI_ARGS="-h $REDIS_HOST -p $REDIS_PORT"
if [ -n "$REDIS_PASSWORD" ]; then
  CLI_ARGS="$CLI_ARGS -a $REDIS_PASSWORD"
fi

echo "Waiting for Redis to become available at $REDIS_HOST:$REDIS_PORT..."
# Loop until Redis responds with PONG, which confirms it's ready for commands.
until redis-cli $CLI_ARGS ping | grep -q 'PONG'; do
  echo "Could not connect to Redis at $REDIS_HOST:$REDIS_PORT. Retrying..."
  sleep 2
done
echo "Redis is available. Proceeding with Nitter configuration."

# --- Update Hostname ---
# Check if NITTER_HOSTNAME is set and not empty, then update the config.
if [ -n "$NITTER_HOSTNAME" ]; then
  # Strip protocol (e.g., https://) from the hostname
  HOSTNAME_NO_PROTO=${NITTER_HOSTNAME#*//}
  echo "Updating hostname to $HOSTNAME_NO_PROTO"
  # Use sed's pipe delimiter for URLs to avoid escaping slashes.
  sed -i "s|hostname = \".*\"|hostname = \"$HOSTNAME_NO_PROTO\"|" "$CONFIG_FILE"
else
  echo "Warning: NITTER_HOSTNAME environment variable not set."
fi

# --- Update Redis Configuration ---
echo "Configuring Redis for Nitter..."

# Remove any existing Redis config to avoid conflicts.
sed -i '/redisHost/d' "$CONFIG_FILE"
sed -i '/redisPort/d' "$CONFIG_FILE"
sed -i '/redisPassword/d' "$CONFIG_FILE"
sed -i '/redisUrl/d' "$CONFIG_FILE"

# Add the new configuration under the [Cache] section from environment variables.
CONFIG_STRING="redisHost = \"$REDIS_HOST\"\nredisPort = $REDIS_PORT"
if [ -n "$REDIS_PASSWORD" ]; then
  CONFIG_STRING="$CONFIG_STRING\nredisPassword = \"$REDIS_PASSWORD\""
fi

# Insert the Redis configuration into nitter.conf under the [Cache] section.
awk -v config="$CONFIG_STRING" '/\[Cache\]/ {print; print config; next} 1' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

echo "Redis configuration updated from environment variables."

# --- Start Nitter ---
echo "Starting Nitter..."
# Execute the main Nitter binary.
exec /src/nitter


# Only add the password if it's provided.
if [ -n "$REDIS_PASSWORD" ]; then
  CONFIG_STRING="$CONFIG_STRING\nredisPassword = \"$REDIS_PASSWORD\""
fi

sed -i "/\[Cache\]/a $CONFIG_STRING" "$CONFIG_FILE"

echo "Redis configuration updated from environment variables."



# --- Start Nitter ---
echo "Configuration complete. Starting Nitter..."
# Execute the main nitter application process.
# This replaces the shell process, making Nitter the main container process.
exec /src/nitter
