# Deployment Guide

This guide covers deploying Scraparr in various environments.

## Quick Start with Docker Compose

The simplest way to run Scraparr is using Docker Compose:

```bash
# Clone repository
git clone https://github.com/depeter/scraparr.git
cd scraparr

# Copy environment file
cp .env.example .env

# Edit .env with your settings (optional)
nano .env

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://scraparr:scraparr@localhost:5432/scraparr"

# Run server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set environment
export REACT_APP_API_URL=http://localhost:8000

# Start development server
npm start
```

### Database

```bash
# Start PostgreSQL with Docker
docker run -d \
  --name scraparr-postgres \
  -e POSTGRES_USER=scraparr \
  -e POSTGRES_PASSWORD=scraparr \
  -e POSTGRES_DB=scraparr \
  -p 5432:5432 \
  postgres:15-alpine
```

## Production Deployment

### Prerequisites

- Docker and Docker Compose
- PostgreSQL 15+ (or use Docker)
- Domain name (optional)
- SSL certificate (optional, recommended)

### Step 1: Prepare Environment

```bash
# Clone repository
git clone https://github.com/depeter/scraparr.git
cd scraparr

# Create production environment file
cp .env.example .env
```

Edit `.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://scraparr:STRONG_PASSWORD@postgres:5432/scraparr

# Backend
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-change-this

# CORS (update with your domain)
CORS_ORIGINS=["https://yourdomain.com", "https://api.yourdomain.com"]
```

### Step 2: Build and Start Services

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### Step 3: Initialize Database

The database will be automatically initialized on first startup. Check logs:

```bash
docker-compose logs backend
```

### Step 4: Configure Reverse Proxy (Optional)

If you want to use a custom domain with SSL, configure a reverse proxy like Nginx or Caddy.

#### Nginx Example

```nginx
server {
    listen 80;
    server_name scraparr.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name scraparr.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://scraparr:scraparr@postgres:5432/scraparr |
| `DEBUG` | Enable debug mode | False |
| `SECRET_KEY` | Secret key for security | (required in production) |
| `CORS_ORIGINS` | Allowed CORS origins | ["http://localhost:3000"] |
| `MAX_CONCURRENT_SCRAPERS` | Max concurrent scrapers | 5 |
| `SCRAPER_TIMEOUT` | Scraper timeout in seconds | 300 |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API URL | http://localhost:8000 |

## Database Backup

### Manual Backup

```bash
# Backup database
docker exec scraparr-postgres pg_dump -U scraparr scraparr > backup.sql

# Restore database
docker exec -i scraparr-postgres psql -U scraparr scraparr < backup.sql
```

### Automated Backups

Add a cron job:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup-script.sh
```

Example backup script:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/scraparr"
mkdir -p $BACKUP_DIR

docker exec scraparr-postgres pg_dump -U scraparr scraparr | \
  gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database health
docker exec scraparr-postgres pg_isready -U scraparr
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

## Maintenance

### Update Scraparr

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Database Migrations

Scraparr automatically creates tables on startup. If you need to run manual migrations:

```bash
# Access backend container
docker exec -it scraparr-backend bash

# Run migrations (if using Alembic)
alembic upgrade head
```

### Clean Up

```bash
# Remove old executions (example SQL)
docker exec -it scraparr-postgres psql -U scraparr scraparr -c \
  "DELETE FROM executions WHERE started_at < NOW() - INTERVAL '30 days';"

# Remove unused Docker images
docker system prune -a
```

## Scaling

### Increase Concurrent Scrapers

Edit `.env`:

```env
MAX_CONCURRENT_SCRAPERS=10
```

Restart backend:

```bash
docker-compose restart backend
```

### Multiple Backend Instances

Use a load balancer to distribute traffic across multiple backend instances:

```yaml
# docker-compose.yml
services:
  backend-1:
    build: ...
    environment:
      INSTANCE_ID: 1

  backend-2:
    build: ...
    environment:
      INSTANCE_ID: 2

  load-balancer:
    image: nginx:alpine
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    ports:
      - "8000:80"
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Database not ready: Wait a few seconds and restart
# - Port conflict: Change BACKEND_PORT in .env
```

### Database connection errors

```bash
# Verify database is running
docker-compose ps postgres

# Check connectivity
docker exec scraparr-backend pg_isready -h postgres -U scraparr
```

### Frontend can't connect to backend

1. Check `REACT_APP_API_URL` in frontend environment
2. Verify CORS settings in backend `.env`
3. Check browser console for errors

### Scraper fails to load

1. Verify module path and class name
2. Check scraper file exists in `scrapers/` directory
3. Review execution logs for detailed error

## Security Recommendations

1. **Change default passwords** in `.env`
2. **Use strong SECRET_KEY** (generate with `openssl rand -hex 32`)
3. **Enable SSL/TLS** in production
4. **Restrict CORS origins** to your domain only
5. **Keep dependencies updated**: `pip install -U -r requirements.txt`
6. **Regular backups** of database
7. **Monitor logs** for suspicious activity
8. **Use firewall** to restrict access to ports

## Support

For issues and questions:
- GitHub Issues: https://github.com/depeter/scraparr/issues
- Documentation: Check `docs/` directory
- Examples: See `scrapers/example_*.py`
