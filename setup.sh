#!/bin/bash
# ============================================================
# Infrest AI Service — One-Command Setup
# Run this once after unzipping the project.
# ============================================================

set -e

echo "============================================"
echo "  Infrest AI Service — Setup"
echo "============================================"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running."
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "[1/5] Starting PostgreSQL and Redis..."
docker compose up db redis -d --wait

echo "[2/5] Waiting for database to be ready..."
sleep 5

echo "[3/5] Loading database schema..."
docker exec -i infrest-db psql -U infrest -d infrest_erp < database/sql/01_schema.sql

echo "[4/5] Loading seed data..."
for file in database/seed/*.csv; do
    if [ -f "$file" ]; then
        table=$(basename "$file" .csv)
        echo "  Loading $table..."
        docker exec -i infrest-db psql -U infrest -d infrest_erp \
            -c "\COPY $table FROM STDIN CSV HEADER" < "$file"
    fi
done

echo "[5/5] Setting up Python environment..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --quiet

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env and add your OPENAI_API_KEY"
echo "  2. Run the server:"
echo "     cd backend"
echo "     source venv/bin/activate"
echo "     uvicorn app.main:app --port 8090 --reload"
echo "  3. Open http://localhost:8090/docs to test"
echo ""
