# Hello-World Heartbeat
# Production-ready Docker image for heartbeat logging

FROM python:3.11-slim

ARG VERSION=unknown
ENV VERSION=$VERSION

LABEL maintainer="rprakashdass"
LABEL version="${VERSION}"
LABEL description="Personal Platform Heartbeat Logger"

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/app.py .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Run as non-root user
USER appuser

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the heartbeat logger
ENTRYPOINT ["python", "app.py"]
CMD ["--format", "text"]
