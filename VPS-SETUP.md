# VPS Setup & Deployment Guide

## 📋 Informații VPS

**Provider:** Romarg (România)
**IP:** 89.45.83.59
**User:** root
**OS:** Ubuntu 24.04 LTS
**Specs:** 4GB RAM, 2 vCPU, 50GB SSD

---

## 🌐 Accesuri

### Dashboard

- **URL:** http://89.45.83.59
- **Username:** Doarazi
- **Password:** Cascaval2026!

### Logs Live

- **URL:** http://89.45.83.59/logs
- Click "Start Live" pentru logs în timp real

### SSH

**Conectare simplă:**

```bash
ssh root@89.45.83.59
# Password: pRv?wkb?p1eDr7
```

**Conectare cu sshpass (fără prompt parolă):**

```bash
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59
```

**Conectare + comandă directă:**

```bash
# Restart service
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl restart betfair-bot && sleep 5 && systemctl status betfair-bot"

# Vezi logs
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "journalctl -u betfair-bot -n 50 --no-pager"

# Rebuild frontend
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "cd /opt/betfair-bot/frontend && npm run build"
```

---

## 🚀 Deployment

### Deploy Rapid (1 comandă)

```bash
./deploy.sh "descriere modificare"
```

**Ce face:**

1. Git add + commit + push
2. SSH pe VPS + pull
3. Restart backend service
4. Verifică status
5. Arată logs recente

**Script complet (`deploy.sh`):**

```bash
#!/bin/bash

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting deployment...${NC}"

# Get commit message from argument or use default
COMMIT_MSG="${1:-Update}"

# Add all changes
echo -e "${BLUE}📦 Adding changes...${NC}"
git add .

# Commit
echo -e "${BLUE}💾 Committing: $COMMIT_MSG${NC}"
git commit -m "$COMMIT_MSG"

# Push to GitHub
echo -e "${BLUE}⬆️  Pushing to GitHub...${NC}"
git push origin main

# Deploy to VPS
echo -e "${BLUE}🔄 Deploying to VPS...${NC}"
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 << 'EOF'
cd /opt/betfair-bot

echo "Pulling latest code..."
git pull origin main

echo "Restarting backend..."
systemctl restart betfair-bot

# Wait for service to start
sleep 3

# Check if service is running
if systemctl is-active --quiet betfair-bot; then
    echo "✅ Backend restarted"
else
    echo "❌ Backend failed to start"
    systemctl status betfair-bot
    exit 1
fi
EOF

# Check deployment status
echo -e "${BLUE}📊 Checking status...${NC}"
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl is-active betfair-bot"

if [ $? -eq 0 ]; then
    echo "✅ Service is running"
else
    echo "❌ Service is not running"
fi

# Show recent logs
echo -e "${BLUE}📋 Recent logs:${NC}"
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "journalctl -u betfair-bot -n 20 --no-pager"

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Dashboard: http://89.45.83.59${NC}"
echo -e "${GREEN}📊 Logs: http://89.45.83.59/logs${NC}"
```

**Permisiuni (prima dată):**

```bash
chmod +x deploy.sh
```

### Exemple

```bash
./deploy.sh "fix: corectare bug verificare rezultate"
./deploy.sh "feat: adaugare validare stake minim"
./deploy.sh "refactor: optimizare cod staking"
```

---

## 🛠️ Comenzi Utile

### Status & Logs (de pe local)

```bash
# Status serviciu
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl status betfair-bot"

# Logs live (Ctrl+C pentru a opri)
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "journalctl -u betfair-bot -f"

# Ultimele 100 linii
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "journalctl -u betfair-bot -n 100 --no-pager"

# Logs cu erori
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "journalctl -u betfair-bot -p err --no-pager"
```

### Control Serviciu (de pe local)

```bash
# Restart
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl restart betfair-bot"

# Stop
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl stop betfair-bot"

# Start
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl start betfair-bot"

# Restart + verificare
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "systemctl restart betfair-bot && sleep 3 && systemctl status betfair-bot"
```

### Update Manual (de pe local)

```bash
# Pull + restart
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "cd /opt/betfair-bot && git pull && systemctl restart betfair-bot"

# Rebuild frontend
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "cd /opt/betfair-bot/frontend && npm run build"
```

### Verificări (de pe local)

```bash
# Verifică .env
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "cat /opt/betfair-bot/backend/.env"

# Verifică certificate Betfair
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "ls -la /opt/betfair-bot/backend/certs/"

# Verifică Google credentials
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "ls -la /opt/betfair-bot/backend/credentials/"

# Verifică disk space
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "df -h"

# Verifică memory usage
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 "free -h"
```

### Comenzi pe VPS (după SSH)

```bash
# Status serviciu
systemctl status betfair-bot

# Logs live
journalctl -u betfair-bot -f

# Ultimele 100 linii
journalctl -u betfair-bot -n 100 --no-pager
```

### Script Helper

```bash
# Pe VPS există script helper
./bot-commands.sh logs          # Logs live
./bot-commands.sh logs-last     # Ultimele 100 linii
./bot-commands.sh status        # Status serviciu
./bot-commands.sh restart       # Restart bot
./bot-commands.sh update        # Update + restart
```

---

## 📁 Structură Fișiere pe VPS

```
/opt/betfair-bot/
├── backend/
│   ├── app/
│   │   ├── main.py              # Entry point
│   │   ├── config.py            # Configurații
│   │   ├── api/
│   │   │   ├── routes.py        # API routes
│   │   │   ├── logs.py          # Logs endpoint
│   │   │   └── websocket.py     # WebSocket
│   │   ├── services/
│   │   │   ├── bot_engine.py    # Core bot logic
│   │   │   ├── betfair_client.py # Betfair API
│   │   │   ├── google_sheets.py  # Google Sheets
│   │   │   └── staking.py       # Staking logic
│   │   └── models/
│   ├── certs/
│   │   ├── betfair.crt          # Betfair SSL cert
│   │   └── betfair.key          # Betfair SSL key
│   ├── credentials/
│   │   └── google_service_account.json
│   ├── venv/                    # Python virtual env
│   ├── .env                     # Environment variables
│   └── requirements.txt
├── frontend/
│   ├── dist/                    # Built frontend
│   └── src/
└── deploy.sh                    # Local deploy script

/etc/systemd/system/
└── betfair-bot.service          # Systemd service

/etc/nginx/sites-available/
└── betfair-bot                  # Nginx config

/root/
└── bot-commands.sh              # Helper script
```

---

## ⚙️ Configurații

### Environment Variables (.env)

```bash
# Betfair API
BETFAIR_APP_KEY=06z7iWIfHewvFOvk
BETFAIR_USERNAME=tone.claudiu23@gmail.com
BETFAIR_PASSWORD=Paroladeparior03.
BETFAIR_CERT_PATH=./certs/betfair.crt
BETFAIR_KEY_PATH=./certs/betfair.key

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/google_service_account.json
GOOGLE_SHEETS_SPREADSHEET_ID=1XQyFy5G0QHwcpYU6hEUllUkqVM5koSRsIfBlpJArbT4

# Bot Configuration
BOT_RUN_HOUR=13
BOT_RUN_MINUTE=0
BOT_INITIAL_STAKE=100.0
BOT_MAX_PROGRESSION_STEPS=7

# Authentication
AUTH_USERNAME=Doarazi
AUTH_PASSWORD=Cascaval2026!
JWT_SECRET=betfair-bot-secret-key-change-in-production

# Claude AI
ANTHROPIC_API_KEY=your_anthropic_api_key

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

### Systemd Service

```ini
[Unit]
Description=Betfair Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/betfair-bot/backend
Environment=PATH=/opt/betfair-bot/backend/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/betfair-bot/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx Config

```nginx
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        root /opt/betfair-bot/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 📅 Scheduler

### Bot Execution

- **Zilnic la 13:00** (Europe/Bucharest)
- Verifică meciurile programate
- Plasează pariuri automat

### Results Check

- **La fiecare 30 minute**
- Verifică pariurile PENDING
- Actualizează statusul (WON/LOST)
- Actualizează progresia echipelor

---

## 🔧 Troubleshooting

### Bot nu pornește

```bash
# Verifică logs
journalctl -u betfair-bot -n 50 --no-pager

# Verifică .env
cat /opt/betfair-bot/backend/.env

# Test manual
cd /opt/betfair-bot/backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend nu se încarcă

```bash
# Verifică nginx
systemctl status nginx
nginx -t

# Rebuild frontend
cd /opt/betfair-bot/frontend
npm run build
systemctl restart nginx
```

### Erori Betfair API

```bash
# Verifică certificatele
ls -la /opt/betfair-bot/backend/certs/

# Test conexiune
cd /opt/betfair-bot/backend
source venv/bin/activate
python -c "from app.services.betfair_client import betfair_client; import asyncio; asyncio.run(betfair_client.connect())"
```

### Erori Google Sheets

```bash
# Verifică credentials
cat /opt/betfair-bot/backend/credentials/google_service_account.json

# Test conexiune
cd /opt/betfair-bot/backend
source venv/bin/activate
python -c "from app.services.google_sheets import google_sheets_client; google_sheets_client.connect(); print(google_sheets_client.is_connected())"
```

---

## 🔐 Securitate

### Firewall (UFW)

```bash
# Status
ufw status

# Permite doar porturile necesare
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw enable
```

### SSH Key (Opțional)

```bash
# Generează pe Mac
ssh-keygen -t rsa -b 4096

# Copiază pe VPS
ssh-copy-id root@89.45.83.59

# Dezactivează password login
# /etc/ssh/sshd_config: PasswordAuthentication no
```

---

## 📊 Monitoring

### Resource Usage

```bash
# CPU & Memory
htop

# Disk usage
df -h

# Service memory
systemctl status betfair-bot
```

### Logs Rotation

```bash
# Configurare automată prin systemd
journalctl --vacuum-time=7d  # Păstrează 7 zile
```

---

## 🆘 Support

### Contact

- **Email:** tone.claudiu23@gmail.com
- **GitHub:** https://github.com/forsitex/Clabot

### Backup Important

- `.env` file
- `certs/` folder
- `credentials/` folder
- Google Sheets Spreadsheet ID

---

## ✅ Checklist Post-Deploy

- [ ] Dashboard accesibil (http://89.45.83.59)
- [ ] Login funcționează
- [ ] Logs live funcționează (/logs)
- [ ] Bot status = RUNNING
- [ ] Scheduler activ (13:00 daily + 30min results)
- [ ] Google Sheets conectat
- [ ] Betfair API conectat
- [ ] Certificatele Betfair valide
- [ ] IP românesc confirmat (89.45.83.59)
