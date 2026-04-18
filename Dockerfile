# Using a slim image for lightweight deployment as requested
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for SQLite and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure data directory exists for volume mounting
RUN mkdir -p /app/data

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose MCP port
EXPOSE 8080

# Set PYTHONPATH and run entrypoint
ENV PYTHONPATH=/app
CMD ["/app/entrypoint.sh"]