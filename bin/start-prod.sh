#!/bin/bash
# ============================================================================
# Agentic AI HR Automation - Start Script (Production Mode)
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
echo -e "${BLUE}  Agentic AI HR Automation - Production Mode${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found. Please create it from env.example${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker-compose.prod.yml exists
if [ ! -f docker-compose.prod.yml ]; then
    echo -e "${YELLOW}⚠️  docker-compose.prod.yml not found${NC}"
    echo -e "${YELLOW}Creating docker-compose.prod.yml from docker-compose.yml...${NC}"
    # Will need to create this file or use docker-compose.yml
    COMPOSE_FILE="docker-compose.yml"
else
    COMPOSE_FILE="docker-compose.prod.yml"
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
            echo "Production Mode Options:"
            echo "  -b, --build     (ignored; images are always rebuilt)"
            echo "  --detach        Run in detached mode (background) [DEFAULT]"
            echo "  --recreate      Recreate containers (removes old containers)"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "Production Features:"
            echo "  • Optimized frontend build"
            echo "  • NGINX static file serving"
            echo "  • No hot reload (faster performance)"
            echo "  • Suitable for deployment"
            echo ""
            echo "Examples:"
            echo "  $0                  # Start in prod mode"
            echo "  $0 -b               # Build and start"
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

echo -e "${BLUE}🏭 Mode: Production (optimized build)${NC}"
echo -e "${BLUE}🐳 Starting with Docker Compose...${NC}"
echo ""

# Stop existing containers if recreate is requested
if [ "$RECREATE" = true ]; then
    echo -e "${YELLOW}🔄 Stopping existing containers...${NC}"
    docker-compose -f "$COMPOSE_FILE" down
    echo ""
fi

# Always rebuild images so dependencies are up to date
echo -e "${YELLOW}🔨 Building Docker images...${NC}"
docker-compose -f "$COMPOSE_FILE" build
echo ""

# Production mode defaults to detached
if [ "$DETACH" = false ]; then
    DETACH=true
fi

echo -e "${GREEN}🚀 Starting services in detached mode...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d
echo ""
echo -e "${GREEN}✅ Services started!${NC}"
echo ""
echo -e "${BLUE}Available Services:${NC}"
echo "  • Backend API:    http://localhost:8000"
echo "  • API Docs:      http://localhost:8000/docs"
echo "  • Frontend:       http://localhost:5173"
echo "  • MinIO Console:  http://localhost:9001"
echo ""
echo -e "${YELLOW}View logs with: docker-compose -f $COMPOSE_FILE logs -f${NC}"
echo -e "${YELLOW}Stop services with: ./bin/stop_prod.sh${NC}"
