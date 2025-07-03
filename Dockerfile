# Use a specific, stable version of the Nitter image
FROM zedeus/nitter:latest

# Nitter runs on port 8080 inside the container
# Render will map this to the public-facing port 443 (HTTPS)
EXPOSE 8080

# Copy our custom nitter.conf file into the container
COPY nitter.conf /src/nitter.conf

# The command to start the Nitter service
CMD ["/src/nitter"]
