#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the path to the config file
CONFIG_FILE="/src/nitter.conf"

# --- Update Hostname ---
# Check if NITTER_HOSTNAME is set and not empty, then update the config.
if [ -n "$NITTER_HOSTNAME" ]; then
  echo "Updating hostname to $NITTER_HOSTNAME"
  # Use sed's pipe delimiter for URLs to avoid escaping slashes.
  sed -i "s|hostname = \".*\"|hostname = \"$NITTER_HOSTNAME\"|" "$CONFIG_FILE"
else
  echo "Warning: NITTER_HOSTNAME environment variable not set."
fi

# --- Update Redis Configuration ---
# Check if REDIS_URL is set and not empty.
if [ -n "$REDIS_URL" ]; then
  echo "Parsing REDIS_URL and updating nitter.conf"

  # Use shell parameter expansion for robust parsing of redis://user:pass@host:port
  # This method is more reliable than awk/sed for various URL formats.

  # 1. Strip protocol (redis:// or rediss://)
  URL_NO_PROTO=${REDIS_URL#*://}

  # 2. Extract host and port
  HOST_PORT=${URL_NO_PROTO#*@}
  REDIS_HOST=${HOST_PORT%:*}
  REDIS_PORT=${HOST_PORT#*:}

  # 3. Extract password
  CREDS=${URL_NO_PROTO%@*}
  REDIS_PASSWORD=${CREDS#*:}

  # Update nitter.conf with the parsed Redis details
  sed -i "s|redisHost = \".*\"|redisHost = \"$REDIS_HOST\"|" "$CONFIG_FILE"
  sed -i "s|redisPort = .*|redisPort = $REDIS_PORT|" "$CONFIG_FILE"
  sed -i "s|redisPassword = \".*\"|redisPassword = \"$REDIS_PASSWORD\"|" "$CONFIG_FILE"

  echo "Redis configured successfully."
else
  echo "Warning: REDIS_URL environment variable not set. Nitter will fail to connect."
fi

# --- Start Nitter ---
echo "Configuration complete. Starting Nitter..."
# Execute the main nitter application process.
# This replaces the shell process, making Nitter the main container process.
exec /src/nitter
