#!/bin/sh
set -e

echo "Configuring Nitter for Northflank deployment..."

# Set the hostname in nitter.conf
if [ -n "$HOSTNAME" ]; then
  echo "Setting hostname to $HOSTNAME"
  sed -i "s/hostname = \".*\"/hostname = \"$HOSTNAME\"/" /src/nitter.conf
else
  echo "Using default hostname: p01--nitter-scraper--6vvf2kxrg48m.code.run"
  sed -i "s/hostname = \".*\"/hostname = \"p01--nitter-scraper--6vvf2kxrg48m.code.run\"/" /src/nitter.conf
fi

# Configure Redis connection - use NF_NITTER_ prefixed variables if available, fall back to non-prefixed
REDIS_HOST_VAR=${NF_NITTER_REDIS_HOST:-${REDIS_HOST:-localhost}}
REDIS_PORT_VAR=${NF_NITTER_REDIS_PORT:-${REDIS_PORT:-6379}}
REDIS_PASSWORD_VAR=${NF_NITTER_REDIS_PASSWORD:-${REDIS_PASSWORD:-}}

echo "Setting Redis host to $REDIS_HOST_VAR"
sed -i "s/redisHost = \".*\"/redisHost = \"$REDIS_HOST_VAR\"/" /src/nitter.conf

echo "Setting Redis port to $REDIS_PORT_VAR"
sed -i "s/redisPort = [0-9]*/redisPort = $REDIS_PORT_VAR/" /src/nitter.conf

if [ -n "$REDIS_PASSWORD_VAR" ] && [ "$REDIS_PASSWORD_VAR" != "" ]; then
  echo "Setting Redis password"
  sed -i "s/redisPassword = \".*\"/redisPassword = \"$REDIS_PASSWORD_VAR\"/" /src/nitter.conf
fi

# Check if Redis is available
echo "Waiting for Redis to be ready..."
MAX_RETRIES=30
RETRY_INTERVAL=2
RETRIES=0

while [ $RETRIES -lt $MAX_RETRIES ]; do
  if redis-cli -h "$REDIS_HOST_VAR" -p "$REDIS_PORT_VAR" ping > /dev/null 2>&1; then
    echo "Redis is ready!"
    break
  else
    echo "Redis not ready yet, retrying in $RETRY_INTERVAL seconds..."
    sleep $RETRY_INTERVAL
    RETRIES=$((RETRIES+1))
  fi
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
  echo "Redis is not available after $MAX_RETRIES retries. Continuing anyway, but Nitter might not work properly."
fi

# In the official zedeus/nitter image, the binary is in /src
echo "Starting Nitter from /src directory..."
cd /src

# The official image has a simple entrypoint that just runs ./nitter
if [ -f "./nitter" ] && [ -x "./nitter" ]; then
  echo "Found Nitter executable at /src/nitter"
  exec ./nitter
else
  echo "ERROR: Could not find Nitter executable at /src/nitter"
  
  # Fallback to searching for the executable using sh-compatible loop
  echo "Searching for nitter executable in common locations..."
  NITTER_PATHS="/app/nitter /nitter /usr/local/bin/nitter /usr/bin/nitter"
  
  for path in $NITTER_PATHS; do
    if [ -f "$path" ] && [ -x "$path" ]; then
      echo "Found Nitter executable at $path"
      cd "$(dirname "$path")"
      exec "./$(basename "$path")"
      exit 0
    fi
  done
  
  # If we get here, we couldn't find the executable
  echo "ERROR: Could not find Nitter executable. Searched common locations."
  echo "Listing files in /src directory:"
  ls -la /src
  
  echo "Searching for nitter executable in the filesystem..."
  find / -name "nitter" -type f -executable 2>/dev/null || echo "No nitter executable found."
  
  exit 1
fi
