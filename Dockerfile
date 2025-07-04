# Start from the official Nitter image as a base
FROM zedeus/nitter:latest

# Switch to root user to install packages
USER root

# Install stunnel for TLS proxy and redis-tools for health checks
RUN apk --no-cache add stunnel redis

# Explicitly create the stunnel directory to ensure it exists
RUN mkdir -p /etc/stunnel

# Copy the stunnel configuration template to the standard location
COPY stunnel.conf.template /etc/stunnel/stunnel.conf.template

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
