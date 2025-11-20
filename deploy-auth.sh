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
WORK_DIR="/home/peter/work/scraparr"

echo "1. Copying backend files to server..."
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp -r \
  backend/app/models/user.py \
  backend/app/schemas/auth.py \
  backend/app/core/security.py \
  backend/app/api/auth.py \
  backend/init_auth.py \
  backend/protect_endpoints.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend_updates/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/models/__init__.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend_updates/models_init.py

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/schemas/__init__.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend_updates/schemas_init.py

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/core/config.py \
  backend/main.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend_updates/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/api/scrapers.py \
  backend/app/api/jobs.py \
  backend/app/api/executions.py \
  backend/app/api/database.py \
  backend/app/api/proxy.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend_updates/api/

echo "2. Copying frontend files to server..."
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp -r \
  frontend/src/contexts \
  frontend/src/components/ProtectedRoute.tsx \
  frontend/src/pages/LoginPage.tsx \
  ${USER}@${SERVER}:${WORK_DIR}/frontend_updates/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/types/index.ts \
  frontend/src/api/client.ts \
  frontend/src/App.tsx \
  ${USER}@${SERVER}:${WORK_DIR}/frontend_updates/

echo "3. Deploying files on server..."
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh ${USER}@${SERVER} << 'ENDSSH'
cd /home/peter/work/scraparr

# Create directories if they don't exist
mkdir -p backend_updates/api
mkdir -p frontend_updates

# Move backend files
mv backend_updates/user.py backend/app/models/
mv backend_updates/auth.py backend/app/schemas/
mv backend_updates/security.py backend/app/core/
mv backend_updates/auth.py backend/app/api/
mv backend_updates/init_auth.py backend/
mv backend_updates/protect_endpoints.py backend/
mv backend_updates/models_init.py backend/app/models/__init__.py
mv backend_updates/schemas_init.py backend/app/schemas/__init__.py
mv backend_updates/config.py backend/app/core/
mv backend_updates/main.py backend/
mv backend_updates/api/*.py backend/app/api/

# Move frontend files
mv frontend_updates/contexts frontend/src/
mv frontend_updates/ProtectedRoute.tsx frontend/src/components/
mv frontend_updates/LoginPage.tsx frontend/src/pages/
mv frontend_updates/index.ts frontend/src/types/
mv frontend_updates/client.ts frontend/src/api/
mv frontend_updates/App.tsx frontend/src/

# Copy files into running backend container
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

echo "Backend files copied to container"

# Initialize auth (create users table and admin user)
docker exec scraparr-backend python init_auth.py || echo "Auth already initialized"

echo "4. Building and deploying frontend..."
cd /home/peter/work/scraparr
docker compose build frontend
docker compose up -d frontend

echo "5. Verifying deployment..."
sleep 3
docker logs scraparr-backend --tail 20
docker ps | grep scraparr

echo ""
echo "=== Deployment Complete ==="
echo "Backend: http://scraparr.pm-consulting.be/api"
echo "Frontend: https://scraparr.pm-consulting.be"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
ENDSSH

echo ""
echo "✓ Deployment successful!"
echo "  Access Scraparr at: https://scraparr.pm-consulting.be"
echo "  Login with: admin / admin123"

# Cleanup
rm /tmp/scraparr_pass.sh
