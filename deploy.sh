#!/bin/bash

# Deploy script pentru Betfair Bot
# Usage: ./deploy.sh "commit message"

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting deployment...${NC}"

# Check if commit message provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Commit message required${NC}"
    echo "Usage: ./deploy.sh \"your commit message\""
    exit 1
fi

COMMIT_MSG="$1"

# 1. Git add
echo -e "${BLUE}📦 Adding changes...${NC}"
git add -A

# 2. Git commit
echo -e "${BLUE}💾 Committing: $COMMIT_MSG${NC}"
git commit -m "$COMMIT_MSG" || echo "No changes to commit"

# 3. Git push
echo -e "${BLUE}⬆️  Pushing to GitHub...${NC}"
git push

# 4. Deploy to VPS
echo -e "${BLUE}🔄 Deploying to VPS...${NC}"
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 << 'ENDSSH'
cd /opt/betfair-bot
echo "Pulling latest code..."
git pull
echo "Restarting backend..."
systemctl restart betfair-bot
sleep 3
echo "✅ Backend restarted"
ENDSSH

# 5. Check status
echo -e "${BLUE}📊 Checking status...${NC}"
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl is-active betfair-bot && echo '✅ Service is running' || echo '❌ Service failed'"

# 6. Show recent logs
echo -e "${BLUE}📋 Recent logs:${NC}"
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "journalctl -u betfair-bot -n 20 --no-pager"

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Dashboard: http://89.45.83.59${NC}"
echo -e "${GREEN}📊 Logs: http://89.45.83.59/logs${NC}"
