#!/bin/sh

# Check if REDIS_URL is set and parse it for Nitter
# Upstash format: redis://<user>:<password>@<host>:<port>
if [ -n "$REDIS_URL" ]; then
  # Extract the part after @ (host:port)
  HOST_PORT=$(echo "$REDIS_URL" | cut -d'@' -f2)
  # Extract the part before @ (redis://user:password)
  AUTH_PART=$(echo "$REDIS_URL" | cut -d'@' -f1)

  # Export the variables for Nitter to use from nitter.conf
  export NITTER_REDISHOST=$(echo "$HOST_PORT" | cut -d':' -f1)
  export NITTER_REDISPORT=$(echo "$HOST_PORT" | cut -d':' -f2)
  export NITTER_REDISPASSWORD=$(echo "$AUTH_PART" | cut -d':' -f3)
fi

# Execute the main nitter process
exec /src/nitter 