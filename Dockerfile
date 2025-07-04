# Use a specific, stable version of the Nitter image
# Use a specific, stable version of the Nitter image
FROM zedeus/nitter:latest

# Switch to root to install packages and fix file formats.
USER root

# Install dependencies. stunnel is the TLS proxy, dos2unix is for fixing line endings.
RUN apk add --no-cache netcat-openbsd redis dos2unix stunnel

# Copy all application files.
COPY nitter.conf /src/nitter.conf
COPY sessions.jsonl /src/sessions.jsonl
COPY entrypoint.sh /src/entrypoint.sh
COPY stunnel.conf.template /src/stunnel.conf.template

# Make the script executable and fix line endings in one step.
# This is the definitive fix based on the diagnostic logs.
RUN chmod +x /src/entrypoint.sh && \
    dos2unix /src/entrypoint.sh && \
    apk del dos2unix

# Nitter runs on port 8080 inside the container.
EXPOSE 8080

# Switch back to the non-root user for security before running the application.
USER nitter

# Use ENTRYPOINT to run the container as an executable, as per Docker best practices.
ENTRYPOINT ["/src/entrypoint.sh"]
