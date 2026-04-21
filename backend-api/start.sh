#!/bin/sh

echo "==> Running database migrations..."
RETRIES=5
COUNT=0
until alembic upgrade head; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$RETRIES" ]; then
        echo "WARNING: migrations failed after $RETRIES attempts — starting server anyway"
        break
    fi
    echo "Migration attempt $COUNT failed, retrying in 5s..."
    sleep 5
done

echo "==> Starting server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
