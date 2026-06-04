FROM python:3.11-slim
WORKDIR /app
RUN pip install kubernetes --no-cache-dir
COPY pvc_usage.py .
CMD ["python", "pvc_usage.py"]
