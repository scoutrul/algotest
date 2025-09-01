#!/bin/bash

# Docker Run Script for BackTest Trading Bot
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Default values
MODE="dev"
COMPOSE_FILE="docker-compose.dev.yml"
SERVICES=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -s|--services)
            SERVICES="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -m, --mode MODE        Run mode: dev, prod, or custom (default: dev)"
            echo "  -f, --file FILE        Custom docker-compose file (default: auto-detected)"
            echo "  -s, --services LIST    Comma-separated list of services to run"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                     # Run in development mode"
            echo "  $0 -m prod             # Run in production mode"
            echo "  $0 -s backend          # Run only backend service"
            echo "  $0 -f custom.yml       # Use custom compose file"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Auto-detect compose file based on mode
if [[ "$MODE" == "prod" ]]; then
    COMPOSE_FILE="docker-compose.yml"
    print_status "Production mode detected, using $COMPOSE_FILE"
elif [[ "$MODE" == "dev" ]]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    print_status "Development mode detected, using $COMPOSE_FILE"
fi

# Check if compose file exists
if [[ ! -f "$COMPOSE_FILE" ]]; then
    print_error "Docker Compose file not found: $COMPOSE_FILE"
    exit 1
fi

print_header "🚀 Starting BackTest Trading Bot in $MODE mode..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Build images if they don't exist
print_status "Checking if images exist..."
if [[ -z "$(docker images -q backtest-backend:latest 2> /dev/null)" ]]; then
    print_warning "Backend image not found. Building..."
    cd backend
    docker build -t backtest-backend:latest .
    cd ..
fi

if [[ -z "$(docker images -q backtest-frontend:latest 2> /dev/null)" ]]; then
    print_warning "Frontend image not found. Building..."
    cd frontend
    docker build -t backtest-frontend:latest .
    cd ..
fi

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose -f "$COMPOSE_FILE" down

# Start services
print_status "Starting services with $COMPOSE_FILE..."
if [[ -n "$SERVICES" ]]; then
    print_status "Running services: $SERVICES"
    docker-compose -f "$COMPOSE_FILE" up -d $SERVICES
else
    docker-compose -f "$COMPOSE_FILE" up -d
fi

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check service status
print_status "Checking service status..."
docker-compose -f "$COMPOSE_FILE" ps

# Show logs
print_status "Showing recent logs..."
docker-compose -f "$COMPOSE_FILE" logs --tail=20

echo ""
print_header "🎉 BackTest Trading Bot is starting up!"
echo ""
echo "Services:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:80 (prod) or http://localhost:5173 (dev)"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "To view logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""
echo "To restart services:"
echo "  docker-compose -f $COMPOSE_FILE restart"
