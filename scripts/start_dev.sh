#!/bin/bash
# SentinelOps Development Startup Script
# Usage: ./scripts/start_dev.sh

# 1. Colors for logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Ensure we're in the repository root
cd "$(dirname "$0")/.." || exit

echo -e "${BLUE}>>> Starting SentinelOps Development Environment...${NC}"

# 2. Check for .env file
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found. Please create one from .env.example.${NC}"
    exit 1
fi

# 3. Start Docker dependencies
echo -e "${BLUE}>>> Starting Docker dependencies (Postgres, OpenSearch)...${NC}"
docker compose up -d

# 4. Wait for Postgres to be ready
echo -e "${BLUE}>>> Waiting for Postgres to be healthy...${NC}"
MAX_RETRIES=30
RETRIES=0
until docker exec sentinelops-postgres pg_isready -U postgres > /dev/null 2>&1 || [ $RETRIES -eq $MAX_RETRIES ]; do
  echo -n "."
  sleep 1
  ((RETRIES++))
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
    echo -e "${RED}[TIMEOUT] Postgres failed to become healthy.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK]${NC}"

# 5. Run Database Migrations
echo -e "${BLUE}>>> Running DB Migrations (Alembic)...${NC}"
./.venv/bin/alembic upgrade head
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Alembic migrations failed.${NC}"
    exit 1
fi

# 6. Start Services in Background
echo -e "${BLUE}>>> Launching Services...${NC}"

# Perception Engine (Port 8001)
echo -e "${BLUE}>>> Starting Perception Engine on http://localhost:8001...${NC}"
(cd perception_engine && ../.venv/bin/uvicorn server:app --port 8001 --host 0.0.0.0) > /dev/null 2>&1 &
PERCEPTION_PID=$!

# SentinelOps Agent (Port 8000)
echo -e "${BLUE}>>> Starting SentinelOps Agent on http://localhost:8000...${NC}"
./.venv/bin/uvicorn agent.main:app --port 8000 --host 0.0.0.0 > /dev/null 2>&1 &
AGENT_PID=$!

# Dashboard (Port 5173)
echo -e "${BLUE}>>> Starting Dashboard on http://localhost:5173...${NC}"
(cd dashboard && npm run dev) > /dev/null 2>&1 &
DASHBOARD_PID=$!

# 7. Cleanup on Exit
function cleanup {
    echo -e "\n${YELLOW}>>> Shutting down services (PIDs: $PERCEPTION_PID $AGENT_PID $DASHBOARD_PID)...${NC}"
    kill "$PERCEPTION_PID" "$AGENT_PID" "$DASHBOARD_PID" 2>/dev/null
    # Optional: docker compose down (can be slow, maybe leave up if preferred)
    echo -e "${GREEN}>>> Done.${NC}"
    exit
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}>>> All services are running!${NC}"
echo -e "${BLUE}Dashboard:${NC} http://localhost:5173"
echo -e "${BLUE}Agent API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}Perception Docs:${NC} http://localhost:8001/docs"
echo -e "${YELLOW}Press [Ctrl+C] to stop all backend/frontend services.${NC}"

# Keep script running
wait
