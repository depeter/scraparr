#!/bin/bash
#
# Consolidated Scraparr Deployment Script
# Deploys the unified Scraparr web application with all scrapers to scraparr server
#

set -e  # Exit on error

SERVER="scraparr"
USER="peter"
PASSWORD="nomansland"

echo "========================================="
echo "Scraparr Deployment to $SERVER"
echo "========================================="
echo ""

# Check if rsync and sshpass are installed
if ! command -v rsync &> /dev/null; then
    echo "Installing rsync..."
    sudo apt-get update && sudo apt-get install -y rsync
fi

if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass..."
    sudo apt-get update && sudo apt-get install -y sshpass
fi

echo "Step 1: Preparing deployment..."
echo "-------------------------------------------"

# Create work directory on server
echo "Ensuring work directory exists on server..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $USER@$SERVER \
  "mkdir -p /home/peter/work"

echo ""
echo "Step 2: Transferring Scraparr application..."
echo "-------------------------------------------"

# Use rsync to sync the entire project
echo "Syncing files (this may take a moment)..."
rsync -avz --delete --progress \
  -e "sshpass -p '$PASSWORD' ssh -o StrictHostKeyChecking=no" \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'venv' \
  --exclude '.env' \
  --exclude 'frontend/build' \
  /home/peter/work/scraparr/ \
  $USER@$SERVER:/home/peter/work/scraparr/

echo ""
echo "Step 3: Setting up environment files..."
echo "-------------------------------------------"

# Create .env file for Scraparr web application if it doesn't exist
echo "Creating .env file (if not exists)..."
sshpass -p "$PASSWORD" ssh $USER@$SERVER "cd /home/peter/work/scraparr && if [ ! -f .env ]; then cat > .env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://scraparr:scraparr@postgres:5432/scraparr
DEBUG=True
CORS_ORIGINS=[\"http://localhost:3000\", \"http://localhost:8000\", \"http://scraparr:3000\", \"http://scraparr:8000\"]
ENVEOF
echo '.env file created'
else
echo '.env file already exists'
fi"

echo ""
echo "Step 4: Building and starting Docker containers..."
echo "-------------------------------------------"

# Stop any running containers first
echo "Stopping existing containers..."
sshpass -p "$PASSWORD" ssh $USER@$SERVER \
  "cd /home/peter/work/scraparr && docker compose down 2>/dev/null || true"

echo ""
echo "Building Docker images..."
sshpass -p "$PASSWORD" ssh $USER@$SERVER \
  "cd /home/peter/work/scraparr && docker compose build --no-cache"

echo ""
echo "Starting services..."
sshpass -p "$PASSWORD" ssh $USER@$SERVER \
  "cd /home/peter/work/scraparr && docker compose up -d"

echo ""
echo "Waiting for services to start..."
sleep 15

echo ""
echo "Step 5: Verifying deployment..."
echo "-------------------------------------------"

# Check running containers
echo "Running Docker containers:"
sshpass -p "$PASSWORD" ssh $USER@$SERVER \
  "docker ps --filter 'name=scraparr' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

echo ""
echo "Checking service health..."

# Check PostgreSQL
echo -n "PostgreSQL: "
sshpass -p "$PASSWORD" ssh $USER@$SERVER \
  "docker exec scraparr-postgres pg_isready -U scraparr 2>&1 | grep -q 'accepting connections' && echo '✓ Running' || echo '✗ Not ready'"

# Check backend API
echo -n "Backend API: "
sleep 3
sshpass -p "$PASSWORD" ssh $USER@$SERVER \
  "curl -s http://localhost:8000/docs >/dev/null 2>&1 && echo '✓ Running' || echo '✗ Not ready (may need more time)'"

# Check frontend
echo -n "Frontend: "
sshpass -p "$PASSWORD" ssh $USER@$SERVER \
  "curl -s http://localhost:3000 >/dev/null 2>&1 && echo '✓ Running' || echo '✗ Not ready'"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Access your Scraparr installation:"
echo "  - Backend API:    http://scraparr:8000"
echo "  - API Docs:       http://scraparr:8000/docs"
echo "  - Frontend UI:    http://scraparr:3000"
echo ""
echo "Available scrapers:"
echo "  1. Park4Night (park4night_scraper.py)"
echo "  2. UiTinVlaanderen (uitinvlaanderen_scraper.py)"
echo ""
echo "Next steps:"
echo "  1. Register scrapers via API or UI"
echo "  2. Create scraping jobs"
echo "  3. View logs: ssh $USER@$SERVER 'docker logs -f scraparr-backend'"
echo ""
echo "Quick commands:"
echo "  View logs:     ssh $USER@$SERVER 'cd /home/peter/work/scraparr && docker compose logs -f'"
echo "  Restart:       ssh $USER@$SERVER 'cd /home/peter/work/scraparr && docker compose restart'"
echo "  Stop:          ssh $USER@$SERVER 'cd /home/peter/work/scraparr && docker compose down'"
echo ""
echo "Done!"
