#!/bin/bash
# ============================================================================
# Agentic AI HR Automation - Stop Script (Development Mode)
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
echo -e "${BLUE}  Agentic AI HR Automation - Stop Development${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check which compose file to use
if [ -f docker-compose.dev.yml ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

# Parse command line arguments
REMOVE_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --volumes    Remove named volumes (WARNING: deletes data)"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0               # Stop services"
            echo "  $0 -v            # Stop and remove volumes"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}🛑 Stopping development services...${NC}"

if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "${RED}⚠️  WARNING: This will delete all data in volumes!${NC}"
    docker compose -f "$COMPOSE_FILE" down -v
else
    docker compose -f "$COMPOSE_FILE" down
fi

echo ""
echo -e "${GREEN}✅ Development services stopped${NC}"
