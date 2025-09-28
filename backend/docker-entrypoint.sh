#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until python -c "
import psycopg
import os
import time
url = os.environ.get('DATABASE_URL', 'postgresql+psycopg://user:pass@postgres:5432/rdf')
# Convert SQLAlchemy URL to psycopg format
url = url.replace('postgresql+psycopg://', 'postgresql://')
try:
    conn = psycopg.connect(url)
    conn.close()
    print('PostgreSQL is ready!')
except:
    print('PostgreSQL is not ready yet...')
    exit(1)
"; do
  sleep 2
done

echo "Running migrations..."
python -m alembic upgrade head || {
    echo "Creating initial migration..."
    python -m alembic revision --autogenerate -m "Initial migration"
    python -m alembic upgrade head
}

echo "Seeding database..."
python seed_data.py || echo "Seed data already exists or failed - continuing..."

echo "Starting FastAPI server..."
exec "$@"