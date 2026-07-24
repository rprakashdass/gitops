FROM python:3.11-slim

ARG VERSION=unknown
ENV VERSION=$VERSION

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:9999/health', timeout=2)" || exit 1

# Start bot
CMD ["python", "main.py"]
