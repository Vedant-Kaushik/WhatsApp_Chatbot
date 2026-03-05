# Base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Install dependencies
RUN uv sync

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose the application port
EXPOSE 7860

# Use entrypoint script to fix DNS at runtime before starting the app
CMD ["./entrypoint.sh"]
