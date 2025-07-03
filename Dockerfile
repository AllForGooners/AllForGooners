# Use a specific, stable version of the Nitter image
# Use a specific, stable version of the Nitter image
FROM zedeus/nitter:latest

# Switch to root to install packages
USER root

# Install netcat, which provides the `nc` command for TCP connection testing
# Install netcat for basic TCP checks and redis-tools for advanced Redis checks
RUN apk add --no-cache netcat-openbsd redis

# Switch back to the non-root user for security
USER nitter

# Nitter runs on port 8080 inside the container
# Render will map this to the public-facing port 443 (HTTPS)
EXPOSE 8080

# Copy our custom nitter.conf file into the container
COPY nitter.conf /src/nitter.conf

# Copy the sessions.jsonl file
COPY sessions.jsonl /src/sessions.jsonl

# Copy the entrypoint script and set its permissions in one step
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# The command to start the Nitter service
CMD ["/entrypoint.sh"]
