#!/bin/bash

# Wait for PostgreSQL to be ready
until python -c "import psycopg2; psycopg2.connect(dbname='$POSTGRES_DB', user='$POSTGRES_USER', password='$POSTGRES_PASSWORD', host='127.0.0.1', port='5432')" 2>/dev/null; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 1
done

# Wait for Redis to be ready
until python -c "import redis; redis.Redis(host='127.0.0.1', port=6379).ping()" 2>/dev/null; do
  echo "Waiting for Redis to be ready..."
  sleep 1
done

# Apply database migrations
echo "Applying database migrations..."
python IUW/manage.py migrate

# Create superuser if needed
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Creating superuser..."
  python IUW/manage.py createsuperuser --noinput \
    --email $DJANGO_SUPERUSER_EMAIL \
    --username $DJANGO_SUPERUSER_USERNAME || true
fi

# Start the application
exec "$@" 