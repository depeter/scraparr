#!/bin/bash
set -e

echo "=== Scraparr Authentication Deployment ==="
echo ""

# Setup SSH password helper
cat > /tmp/scraparr_pass.sh << 'EOF'
#!/bin/sh
echo "nomansland"
EOF
chmod +x /tmp/scraparr_pass.sh

SERVER="scraparr"
USER="peter"
WORK_DIR="/home/peter/scraparr"

cd /home/peter/work/scraparr

echo "1. Copying backend files directly to server backend directory..."

# Copy new files
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/models/user.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/models/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/schemas/auth.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/schemas/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/core/security.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/core/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/api/auth.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/api/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/init_auth.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/

# Copy updated files
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/models/__init__.py \
  backend/app/schemas/__init__.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/models/ && \
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/schemas/__init__.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/schemas/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/core/config.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/core/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/main.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/api/scrapers.py \
  backend/app/api/jobs.py \
  backend/app/api/executions.py \
  backend/app/api/database.py \
  backend/app/api/proxy.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/api/

echo "2. Copying frontend files..."

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/types/index.ts \
  ${USER}@${SERVER}:${WORK_DIR}/frontend/src/types/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/api/client.ts \
  ${USER}@${SERVER}:${WORK_DIR}/frontend/src/api/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/App.tsx \
  ${USER}@${SERVER}:${WORK_DIR}/frontend/src/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/pages/LoginPage.tsx \
  ${USER}@${SERVER}:${WORK_DIR}/frontend/src/pages/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/components/ProtectedRoute.tsx \
  ${USER}@${SERVER}:${WORK_DIR}/frontend/src/components/

echo "Creating contexts directory and copying AuthContext..."
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh ${USER}@${SERVER} "mkdir -p ${WORK_DIR}/frontend/src/contexts"

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/contexts/AuthContext.tsx \
  ${USER}@${SERVER}:${WORK_DIR}/frontend/src/contexts/

echo "3. Deploying to Docker containers..."
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh ${USER}@${SERVER} << 'ENDSSH'
cd /home/peter/scraparr

# Copy backend files to running container
docker cp backend/app/models/user.py scraparr-backend:/app/app/models/
docker cp backend/app/schemas/auth.py scraparr-backend:/app/app/schemas/
docker cp backend/app/core/security.py scraparr-backend:/app/app/core/
docker cp backend/app/api/auth.py scraparr-backend:/app/app/api/
docker cp backend/app/models/__init__.py scraparr-backend:/app/app/models/
docker cp backend/app/schemas/__init__.py scraparr-backend:/app/app/schemas/
docker cp backend/app/core/config.py scraparr-backend:/app/app/core/
docker cp backend/main.py scraparr-backend:/app/
docker cp backend/app/api/scrapers.py scraparr-backend:/app/app/api/
docker cp backend/app/api/jobs.py scraparr-backend:/app/app/api/
docker cp backend/app/api/executions.py scraparr-backend:/app/app/api/
docker cp backend/app/api/database.py scraparr-backend:/app/app/api/
docker cp backend/app/api/proxy.py scraparr-backend:/app/app/api/

echo "✓ Backend files copied to container"

# Initialize auth database
docker cp backend/init_auth.py scraparr-backend:/app/
echo "Running auth initialization..."
docker exec scraparr-backend python /app/init_auth.py 2>&1

echo "4. Building and restarting frontend..."
cd /home/peter/scraparr
docker compose build frontend
docker compose up -d frontend

sleep 5

echo "5. Verifying deployment..."
docker ps | grep scraparr
echo ""
docker logs scraparr-backend --tail 10

echo ""
echo "=== Deployment Complete ==="
ENDSSH

echo ""
echo "✓ Authentication deployment successful!"
echo ""
echo "Access Scraparr at: https://scraparr.pm-consulting.be"
echo "Login credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "⚠ IMPORTANT: Change the admin password after first login!"

# Cleanup
rm /tmp/scraparr_pass.sh
