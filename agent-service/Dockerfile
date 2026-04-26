FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

# SERVICE env var selects the process to run:
#   (unset / "api")  → FastAPI  (Agent Service)
#   "worker"         → Celery executor  (Agent Worker)
#   "beat"           → Celery scheduler (Agent Beat)
CMD ["sh", "-c", "\
  if [ \"$SERVICE\" = 'worker' ]; then \
    exec celery -A worker.celery_app worker --loglevel=info --concurrency=2 -Q agent; \
  elif [ \"$SERVICE\" = 'beat' ]; then \
    exec celery -A worker.celery_app beat --loglevel=info --scheduler celery.beat.PersistentScheduler; \
  else \
    exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}; \
  fi"]
