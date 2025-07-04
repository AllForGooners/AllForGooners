# Use a specific, stable version of the Nitter image
# Use a specific, stable version of the Nitter image
FROM zedeus/nitter:latest

# Switch to root to install packages and fix file formats.
USER root

# Install dependencies. dos2unix is critical for fixing Windows line endings.
RUN apk add --no-cache netcat-openbsd redis dos2unix

# Copy all application files.
COPY nitter.conf /src/nitter.conf
COPY sessions.jsonl /src/sessions.jsonl
COPY --chmod=755 entrypoint.sh /src/entrypoint.sh

# Convert the entrypoint script from Windows to Unix format.
# This is the definitive fix for the "Permission denied" error on Windows.
# We then remove dos2unix to keep the final image clean.
RUN dos2unix /src/entrypoint.sh && \
    apk del dos2unix

# Nitter runs on port 8080 inside the container
EXPOSE 8080

# Switch back to the non-root user for security before running the application.
USER nitter

# Use ENTRYPOINT to run the container as an executable, as per Docker best practices.
ENTRYPOINT ["/src/entrypoint.sh"]
