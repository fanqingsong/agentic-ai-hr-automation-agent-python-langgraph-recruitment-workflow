#!/bin/bash
# ============================================================================
# Agentic AI HR Automation - Start Script (Development Mode with Hot Reload)
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  Agentic AI HR Automation - Development Mode${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from env.example...${NC}"
    if [ -f env.example ]; then
        cp env.example .env
        echo -e "${GREEN}✅ Created .env file. Please update it with your configuration.${NC}"
    else
        echo -e "${RED}❌ env.example not found. Cannot create .env file.${NC}"
        exit 1
    fi
    echo ""
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f docker-compose.yml ]; then
    echo -e "${RED}❌ docker-compose.yml not found${NC}"
    exit 1
fi

# Check if docker-compose.dev.yml exists, if not use dev mode
if [ ! -f docker-compose.dev.yml ]; then
    echo -e "${YELLOW}⚠️  docker-compose.dev.yml not found, using docker-compose.yml${NC}"
    COMPOSE_FILE="docker-compose.yml"
else
    COMPOSE_FILE="docker-compose.dev.yml"
fi

# Parse command line arguments
DETACH=false
RECREATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--build)
            # Kept for compatibility; images are always rebuilt
            shift
            ;;
        --detach)
            DETACH=true
            shift
            ;;
        --recreate)
            RECREATE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Development Mode Options:"
            echo "  -b, --build     (ignored; images are always rebuilt)"
            echo "  --detach        Run in detached mode (background)"
            echo "  --recreate      Recreate containers (removes old containers)"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "Development Features:"
            echo "  • Backend Hot Reload:  uvicorn --reload (watches ./backend)"
            echo "  • Frontend Hot Reload: Vite HMR (watches ./frontend/src)"
            echo "  • Source code mounted as volumes"
            echo "  • Faster iteration cycle"
            echo ""
            echo "Examples:"
            echo "  $0                  # Start in dev mode"
            echo "  $0 --detach         # Start in detached mode"
            echo "  $0 -b               # Rebuild and start"
            echo "  $0 --recreate       # Recreate and start"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🔥 Mode: Development (with Hot Reload)${NC}"
echo ""

# Run stop script first so leftover containers are removed
echo -e "${BLUE}🛑 Running stop script to ensure no leftover containers...${NC}"
"$SCRIPT_DIR/stop-dev.sh" 2>/dev/null || true
echo ""

echo -e "${BLUE}🐳 Starting with Docker Compose...${NC}"
echo ""

# Use Docker Compose V2 (docker compose) to avoid ContainerConfig KeyError with older docker-compose v1
COMPOSE_CMD="docker compose -f $COMPOSE_FILE"

# Remove any orphan/legacy backend container that might block creation
# (e.g. 57638dc94917_ai-hr-automation-api from old compose or swarm)
for cid in $(docker ps -aq -f "name=ai-hr-automation-api" 2>/dev/null); do
  echo -e "${YELLOW}Removing conflicting container (name contains ai-hr-automation-api): $cid${NC}"
  docker rm -f "$cid" 2>/dev/null || true
done
for cid in $(docker ps -aq -f "name=hr-automation" 2>/dev/null); do
  echo -e "${YELLOW}Removing conflicting container (name contains hr-automation): $cid${NC}"
  docker rm -f "$cid" 2>/dev/null || true
done

# Stop existing containers if recreate is requested (redundant after above, but keep for --recreate semantics)
if [ "$RECREATE" = true ]; then
    echo -e "${YELLOW}🔄 Recreate: stopping existing containers...${NC}"
    $COMPOSE_CMD down
    echo ""
fi

# Always rebuild images so dependencies (e.g. python-docx) are up to date
echo -e "${YELLOW}🔨 Building Docker images...${NC}"
$COMPOSE_CMD build
echo ""

# Start services
if [ "$DETACH" = true ]; then
    echo -e "${GREEN}🚀 Starting services in detached mode...${NC}"
    $COMPOSE_CMD up -d
    echo ""
    echo -e "${GREEN}✅ Services started!${NC}"
    echo ""
    echo -e "${BLUE}Available Services:${NC}"
    echo "  • Backend API:    http://localhost:8000"
    echo "  • API Docs:      http://localhost:8000/docs"
    echo "  • Frontend:       http://localhost:5173"
    echo "  • MinIO Console:  http://localhost:9001"
    echo ""
    echo -e "${GREEN}🔥 Hot reload: backend (./backend) + frontend (./frontend/src) - changes reflect automatically${NC}"
    echo -e "${YELLOW}View logs with: docker compose -f $COMPOSE_FILE logs -f${NC}"
    echo -e "${YELLOW}Stop services with: ./bin/stop_dev.sh${NC}"
else
    echo -e "${GREEN}🚀 Starting services...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    $COMPOSE_CMD up
fi
