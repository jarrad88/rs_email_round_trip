# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set metadata
LABEL maintainer="Email Delivery Monitor"
LABEL description="Monitors email delivery time between Office 365 and Gmail"
LABEL version="1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY email_delivery_monitor.py .
COPY config.docker.json .

# Create directories for logs and credentials
RUN mkdir -p /app/logs /app/credentials && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Create volume mount points
VOLUME ["/app/logs", "/app/credentials"]

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/logs/email_delivery_monitor.log') else 1)" || exit 1

# Default command
CMD ["python", "email_delivery_monitor.py"]
