#!/bin/sh

# Check if REDIS_URL is set by Render and parse it
if [ -n "$REDIS_URL" ]; then
  # Format: redis://:<password>@[host]:[port]
  export NITTER_REDISHOST=$(echo $REDIS_URL | cut -d'@' -f2 | cut -d':' -f1)
  export NITTER_REDISPORT=$(echo $REDIS_URL | cut -d':' -f4)
  export NITTER_REDISPASSWORD=$(echo $REDIS_URL | cut -d':' -f3 | cut -d'@' -f1)
fi

# Execute the main nitter process
exec /src/nitter 