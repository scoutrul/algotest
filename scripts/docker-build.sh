#!/bin/bash

# Docker Build Script for BackTest Trading Bot
set -e

echo "🐳 Building BackTest Trading Bot Docker containers..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build backend
print_status "Building backend container..."
cd backend
docker build -t backtest-backend:latest .
cd ..

# Build frontend
print_status "Building frontend container..."
cd frontend
docker build -t backtest-frontend:latest .
cd ..

# Build development frontend
print_status "Building development frontend container..."
cd frontend
docker build -f Dockerfile.dev -t backtest-frontend:dev .
cd ..

print_status "All containers built successfully!"
echo ""
echo "Available images:"
docker images | grep backtest
echo ""
echo "To run the application:"
echo "  Development: docker-compose -f docker-compose.dev.yml up"
echo "  Production:  docker-compose up"
echo ""
echo "To stop the application:"
echo "  docker-compose down"
