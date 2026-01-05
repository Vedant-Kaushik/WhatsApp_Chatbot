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

# Expose the application port
EXPOSE 5173

# Run the FastAPI application using uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5173"]