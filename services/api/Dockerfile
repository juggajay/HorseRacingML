# syntax=docker/dockerfile:1
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api/ ./
COPY puntingform_api.py ./puntingform_api.py

ENV PYTHONPATH=/app
ENV PORT=8000

# When run from services/api/ directory (Railway), use main:app
# When run from repo root (Docker Compose), use services.api.main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
