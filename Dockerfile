FROM python:3.11-slim

WORKDIR /app

# Prevents .pyc files and buffers stdout/stderr for clean container logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first (better layer caching on code changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# data/ is expected to be mounted as a volume; create it so the app starts
# cleanly even without the mount (e.g. first boot or local testing).
RUN mkdir -p data/notes

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
 