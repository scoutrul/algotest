# Docker Deployment Guide

## Overview

This guide covers deploying the BackTest Trading Bot using Docker containers for both development and production environments.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │     Redis       │
│   (Nginx)       │◄──►│   (FastAPI)     │◄──►│   (Cache)       │
│   Port 80/443   │    │   Port 8000     │    │   Port 6379     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Nginx Proxy    │
                    │   (Optional)     │
                    │   Port 8080      │
                    └─────────────────┘
```

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

## Quick Start

### 1. Development Mode

```bash
# Start development environment
./scripts/docker-run.sh

# Or manually
docker-compose -f docker-compose.dev.yml up -d
```

**Services:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

### 2. Production Mode

```bash
# Start production environment
./scripts/docker-run.sh -m prod

# Or manually
docker-compose up -d
```

**Services:**
- Backend: http://localhost:8000
- Frontend: http://localhost:80
- Redis: http://localhost:6379

## Docker Images

### Backend Image

**Base:** `python:3.9-slim`
**Size:** ~500MB
**Features:**
- FastAPI application
- Hybrid Strategy Engine
- Binance API integration
- Health checks

**Build:**
```bash
cd backend
docker build -t backtest-backend:latest .
```

### Frontend Image

**Base:** `node:18-alpine` → `nginx:alpine`
**Size:** ~200MB
**Features:**
- Svelte application
- TradingView charts
- Nginx server
- API proxy

**Build:**
```bash
cd frontend
docker build -t backtest-frontend:latest .
```

## Configuration

### Environment Variables

#### Backend
```bash
LOG_LEVEL=INFO                    # Logging level
DEBUG=false                       # Debug mode
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### Frontend
```bash
NODE_ENV=production              # Environment
API_BASE_URL=http://localhost:8000  # Backend URL
```

### Ports

| Service | Internal | External | Description |
|---------|----------|----------|-------------|
| Backend | 8000     | 8000     | FastAPI server |
| Frontend| 80       | 80       | Nginx server |
| Redis   | 6379     | 6379     | Cache server |
| Nginx   | 80       | 8080     | Reverse proxy |

## Docker Compose Files

### Development (`docker-compose.dev.yml`)

- Hot reload enabled
- Volume mounts for live code changes
- Development dependencies
- Debug logging

### Production (`docker-compose.yml`)

- Optimized builds
- Health checks
- Redis caching
- Nginx reverse proxy
- Rate limiting

## Management Commands

### Building Images

```bash
# Build all images
./scripts/docker-build.sh

# Build specific service
docker-compose build backend
docker-compose build frontend
```

### Running Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Start with custom compose file
docker-compose -f custom.yml up -d
```

### Monitoring

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Check service status
docker-compose ps

# View resource usage
docker stats
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop specific service
docker-compose stop backend
```

## Health Checks

### Backend Health Check

```bash
curl http://localhost:8000/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-01T21:00:00",
  "version": "1.0.0",
  "service": "BackTest Trading Bot API"
}
```

### Frontend Health Check

```bash
curl http://localhost:80/health
```

**Expected Response:**
```
healthy
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different ports
docker-compose up -p 8001:8000
```

#### 2. Container Won't Start

```bash
# Check container logs
docker-compose logs backend

# Check container status
docker-compose ps -a

# Restart container
docker-compose restart backend
```

#### 3. Build Failures

```bash
# Clean build cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check Dockerfile syntax
docker build --dry-run .
```

#### 4. Permission Issues

```bash
# Fix file permissions
chmod +x scripts/*.sh

# Fix volume permissions
sudo chown -R $USER:$USER ./backend
sudo chown -R $USER:$USER ./frontend
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
docker-compose up

# View detailed logs
docker-compose logs -f --tail=100
```

## Performance Optimization

### Resource Limits

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

### Caching Strategy

- Redis for API responses
- Nginx for static assets
- Browser caching headers
- Gzip compression

### Scaling

```bash
# Scale backend service
docker-compose up -d --scale backend=3

# Scale with load balancer
docker-compose -f docker-compose.scale.yml up -d
```

## Security

### Best Practices

1. **Non-root users** in containers
2. **Security headers** in Nginx
3. **Rate limiting** on API endpoints
4. **Health checks** for monitoring
5. **Resource limits** to prevent abuse

### Network Security

```yaml
networks:
  backtest-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
    driver_opts:
      com.docker.network.bridge.enable_icc: "false"
```

## Monitoring & Logging

### Log Aggregation

```bash
# View all logs
docker-compose logs -f --tail=100

# Filter logs by service
docker-compose logs -f backend | grep ERROR

# Export logs
docker-compose logs > logs.txt
```

### Metrics

```bash
# Container stats
docker stats --no-stream

# Resource usage
docker system df

# Network usage
docker network ls
```

## Backup & Recovery

### Data Backup

```bash
# Backup Redis data
docker exec backtest-redis redis-cli BGSAVE

# Backup volumes
docker run --rm -v backtest_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz -C /data .

# Backup configuration
cp docker-compose.yml docker-compose.yml.backup
```

### Recovery

```bash
# Restore from backup
docker-compose down
docker volume rm backtest_redis_data
docker volume create backtest_redis_data
docker run --rm -v backtest_redis_data:/data -v $(pwd):/backup alpine tar xzf /backup/redis-backup.tar.gz -C /data

# Restart services
docker-compose up -d
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Build & Deploy

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker images
        run: |
          docker build -t backtest-backend:${{ github.sha }} ./backend
          docker build -t backtest-frontend:${{ github.sha }} ./frontend
      - name: Deploy to production
        run: |
          docker-compose pull
          docker-compose up -d
```

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review container logs
3. Check GitHub issues
4. Create new issue with logs and error details

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Docker Guide](https://fastapi.tiangolo.com/deployment/docker/)
- [Svelte Deployment](https://svelte.dev/docs#deployment)
