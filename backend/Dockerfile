FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Runs as a non-root user in production.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Shell form (not exec array) so $PORT expands — Railway/Render/Fly inject
# their own port at runtime and won't necessarily use 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
