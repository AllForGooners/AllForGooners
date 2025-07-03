#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the path to the config file
CONFIG_FILE="/src/nitter.conf"

# --- Wait for Redis ---
# Loop until a connection to Redis on port 6379 can be established.
# The service name 'redis' is used as the hostname, as defined in docker-compose.yml.
echo "Waiting for Redis to become available..."
# Loop until Redis responds with PONG, which confirms it's ready for commands.
until redis-cli -h redis ping | grep -q 'PONG'; do
  echo "Waiting for Redis to be ready..."
  sleep 1
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
# The source code (src/config.nim) shows the application uses redisHost, redisPort, and redisPassword.
# We will dynamically add these from environment variables for deployment flexibility.

# Remove any existing Redis config to avoid conflicts.
sed -i '/redisHost/d' "$CONFIG_FILE"
sed -i '/redisPort/d' "$CONFIG_FILE"
sed -i '/redisPassword/d' "$CONFIG_FILE"
sed -i '/redisUrl/d' "$CONFIG_FILE"

# Add the new configuration under the [Cache] section from environment variables.
# This script requires REDIS_HOST and REDIS_PORT to be set for cloud deployment.
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
  echo "Error: REDIS_HOST and REDIS_PORT environment variables must be set."
  exit 1
fi

CONFIG_STRING="redisHost = \"$REDIS_HOST\"\nredisPort = $REDIS_PORT"

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
