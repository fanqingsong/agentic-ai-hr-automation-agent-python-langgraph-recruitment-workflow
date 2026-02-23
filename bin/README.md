# Bin Directory

This directory contains utility scripts for managing the Agentic AI HR Automation application.

> **Note:** These scripts only support Docker-based deployment. For local development, please run services directly using Docker Compose.

## Scripts

### `start.sh` - Start the application

Starts the HR Automation backend server using Docker Compose.

```bash
# Start services
bin/start.sh

# Start services in detached mode
bin/start.sh --detach

# Start with rebuild
bin/start.sh -b

# Start detached with rebuild
bin/start.sh -b --detach

# Recreate containers and start
bin/start.sh --recreate
```

#### Options:
- `-b, --build` - Rebuild Docker images before starting
- `--detach` - Run in detached mode (background)
- `--recreate` - Recreate containers (removes old containers)
- `-h, --help` - Show help message

### `stop.sh` - Stop the application

Stops running HR Automation Docker services.

```bash
# Stop services
bin/stop.sh

# Stop services and remove volumes
bin/stop.sh -v
```

#### Options:
- `-v, --volumes` - Remove named volumes (WARNING: deletes data)
- `-h, --help` - Show help message

## Quick Start

1. **First time setup:**
   ```bash
   # Copy environment file
   cp env.example .env

   # Edit .env with your configuration
   nano .env
   ```

2. **Start the application:**
   ```bash
   # Start services
   bin/start.sh

   # Start in detached mode (recommended)
   bin/start.sh --detach
   ```

3. **Access the application:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Frontend: http://localhost:5173 (if started)

4. **Stop the application:**
   ```bash
   bin/stop.sh
   ```

## Development Workflow

```bash
# Start services in detached mode
bin/start.sh --detach

# View logs
docker-compose logs -f

# Run tests in another terminal (if needed)
docker-compose exec backend pytest

# Stop when done
bin/stop.sh
```

## Production Deployment

```bash
# Start all services
bin/start.sh --detach

# View logs
docker-compose logs -f

# Stop all services
bin/stop.sh

# Remove volumes (WARNING: deletes data)
bin/stop.sh -v
```
