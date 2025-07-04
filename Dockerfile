# Start from the official Nitter image as a base
FROM zedeus/nitter:latest

# Switch to root user to install packages
USER root

# Install stunnel for TLS proxy and redis-tools for health checks
RUN apk --no-cache add stunnel redis

# Copy Nitter configuration files to the working directory
COPY nitter.conf /src/nitter.conf
COPY sessions.jsonl /src/sessions.jsonl

# Copy the custom entrypoint script to a standard binary location
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# Nitter runs on port 8080 inside the container.
EXPOSE 8080

# Switch back to the non-root user for security
USER nitter

# Set the entrypoint to our custom script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
