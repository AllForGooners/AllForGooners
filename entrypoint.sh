#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the path to the config file
CONFIG_FILE="/src/nitter.conf"

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
# Check if REDIS_URL is set and not empty, then update the config.
# This is the recommended way to configure Redis for Nitter.
if [ -n "$REDIS_URL" ]; then
  echo "Updating redisUrl in nitter.conf with the provided REDIS_URL"
  # Use sed's pipe delimiter for URLs to avoid escaping slashes.
  sed -i "s|redisUrl = \".*\"|redisUrl = \"$REDIS_URL\"|" "$CONFIG_FILE"
  echo "Redis configured successfully using redisUrl."
else
  echo "Warning: REDIS_URL environment variable not set. Using default Redis config."
fi

# --- Start Nitter ---
echo "Configuration complete. Starting Nitter..."
# Execute the main nitter application process.
# This replaces the shell process, making Nitter the main container process.
exec /src/nitter
