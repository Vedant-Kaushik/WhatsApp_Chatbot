# Base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Fix DNS resolution for Hugging Face Docker containers
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf

# Copy project files
COPY . /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Install dependencies
RUN uv sync

# Expose the application port
EXPOSE 7860

# Run the FastAPI application using uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]