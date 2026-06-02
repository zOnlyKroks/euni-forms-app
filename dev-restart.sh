#!/bin/bash
# Development server restart script for Unix/Linux/Mac
set -e

echo "========================================"
echo "EVE University Forms - Development Server"
echo "========================================"

echo
echo "[1/6] Stopping all services..."
docker compose down

echo
echo "[2/6] Starting database and Redis..."
docker compose up -d mariadb redis

echo
echo "[3/6] Waiting for database to be ready..."
echo "Waiting for MariaDB..."
until docker compose exec mariadb mariadb -u root -p"12345678" -e "SELECT 1;" >/dev/null 2>&1; do
    echo "Waiting for MariaDB..."
    sleep 3
done
echo "✅ Database is ready"

echo
echo "[4/6] Building auth service..."
docker compose build auth

echo
echo "[5/6] Running database migrations..."
docker compose run --rm auth bash -c "cd /app/myauth && python manage.py migrate"
docker compose run --rm auth bash -c "cd /app/myauth && python manage.py migrate euniforms"

echo
echo "[6/6] Collecting static files..."
docker compose run --rm auth bash -c "cd /app/myauth && python manage.py collectstatic --noinput"

echo
echo "Starting development server..."
docker compose up -d auth

echo
echo "========================================"
echo "✅ Development server is ready!"
echo "========================================"
echo
echo "🌐 Access your application at: http://localhost:8000"
echo "👤 Admin panel at: http://localhost:8000/admin"
echo
echo "To view logs: docker compose logs -f auth"
echo "To stop: docker compose down"
echo

# Optional: Create superuser (uncomment if needed)
# echo "Creating superuser..."
# docker compose exec auth bash -c "cd /app/myauth && python manage.py createsuperuser"