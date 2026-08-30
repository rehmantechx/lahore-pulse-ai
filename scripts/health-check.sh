#!/usr/bin/env bash
# health-check.sh — Quick system verification for Lahore Pulse AI
# Run from project root before demo

set -e

echo "=== Lahore Pulse AI — Health Check ==="
echo ""

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:5173"

# 1. Backend health
echo "1. Backend health endpoint..."
HEALTH=$(curl -s "$BACKEND_URL/api/v1/health" 2>/dev/null)
if echo "$HEALTH" | grep -q "status"; then
    echo "   ✅ Backend is running"
else
    echo "   ❌ Backend not responding at $BACKEND_URL"
    echo "   Start with: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir ."
    exit 1
fi

# 2. Predictions endpoint
echo "2. Predictions endpoint..."
PRED=$(curl -s "$BACKEND_URL/api/v1/predictions/latest" 2>/dev/null)
if echo "$PRED" | grep -q "horizon"; then
    echo "   ✅ Predictions are available"
else
    echo "   ⚠️  Predictions endpoint returned unexpected response"
fi

# 3. Observations endpoint
echo "3. Observations endpoint..."
OBS=$(curl -s "$BACKEND_URL/api/v1/observations/latest?limit=1" 2>/dev/null)
if echo "$OBS" | grep -q "pm25"; then
    echo "   ✅ Observations are available"
else
    echo "   ⚠️  Observations endpoint returned unexpected response"
fi

# 4. Stations endpoint
echo "4. Stations endpoint..."
STATIONS=$(curl -s "$BACKEND_URL/api/v1/stations" 2>/dev/null)
if echo "$STATIONS" | grep -q "station_id"; then
    echo "   ✅ Stations are available"
else
    echo "   ⚠️  Stations endpoint returned unexpected response"
fi

# 5. Models endpoint
echo "5. Models registry endpoint..."
MODELS=$(curl -s "$BACKEND_URL/api/v1/models/registry" 2>/dev/null)
if echo "$MODELS" | grep -q "horizon"; then
    echo "   ✅ Model registry is available"
else
    echo "   ⚠️  Models endpoint returned unexpected response"
fi

# 6. Accuracy endpoint
echo "6. Accuracy endpoint..."
ACC=$(curl -s "$BACKEND_URL/api/v1/accuracy/summary" 2>/dev/null)
if echo "$ACC" | grep -q "total"; then
    echo "   ✅ Accuracy tracker is available"
else
    echo "   ⚠️  Accuracy endpoint returned unexpected response"
fi

# 7. Frontend
echo "7. Frontend build check..."
if [ -d "frontend/dist" ]; then
    echo "   ✅ Frontend production build exists"
else
    echo "   ⚠️  No production build found (run: cd frontend && npm run build)"
fi

# 8. Database
echo "8. Database check..."
if [ -f "backend/data/lahore_pulse.db" ]; then
    SIZE=$(stat -f%z "backend/data/lahore_pulse.db" 2>/dev/null || stat --printf="%s" "backend/data/lahore_pulse.db" 2>/dev/null || echo "unknown")
    echo "   ✅ Database found ($SIZE bytes)"
else
    echo "   ❌ Database not found at backend/data/lahore_pulse.db"
fi

echo ""
echo "=== Health check complete ==="
echo ""
echo "To start the system:"
echo "  Backend:  cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir ."
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "To run tests:"
echo "  Backend:  cd backend && python -m pytest tests/ -v --no-header -q --no-file-parallelism"
echo "  Frontend: cd frontend && npx vitest run --pool=forks"
