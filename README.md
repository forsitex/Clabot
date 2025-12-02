# 🎯 Clabot - Betfair Bot Automat

**Bot automat de pariuri sportive cu strategie de progresie**

[![Status](https://img.shields.io/badge/status-production-success)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![Vue.js](https://img.shields.io/badge/vue.js-3-green)]()

---

## 🚀 Quick Start

```bash
# Deploy
./deploy.sh "your commit message"

# Acces Dashboard
http://89.45.83.59
```

---

## 📚 Documentație

**Pentru documentație completă, vezi:**
- **[DOCUMENTATION.md](./DOCUMENTATION.md)** - Documentație completă (arhitectură, funcționalități, API, troubleshooting)
- **[VPS-SETUP.md](./VPS-SETUP.md)** - Setup VPS și deployment

---

## ✨ Features

- ✅ **Plasare automată** pariuri la ore programate
- ✅ **Strategie de progresie** pentru recuperare pierderi
- ✅ **Dashboard web** pentru monitorizare și control
- ✅ **Google Sheets** integration pentru stocare date
- ✅ **Miză inițială per echipă** configurabilă
- ✅ **Verificare automată** rezultate
- ✅ **Filtrare** echipe rezerve/tineret/feminine
- ✅ **WebSocket** pentru actualizări live

---

## 🏗️ Stack Tehnologic

**Backend:** Python 3.12, FastAPI, APScheduler, Betfair API, Google Sheets API  
**Frontend:** Vue.js 3, TypeScript, Vite, TailwindCSS, Pinia  
**Deployment:** VPS Ubuntu 24.04, Nginx, systemd

---

## 📊 Strategie

**Formula:** `(pierdere_cumulată / (cotă - 1)) + miză_inițială`

**Exemplu:**
- Miză inițială: 5 RON
- Step 0: 5 RON → LOST
- Step 1: 15 RON → LOST
- Step 2: 45 RON → WIN → Profit: 2.5 RON ✅

**Caracteristici:**
- Reset automat la WIN
- Stop loss la 7 pași
- Miză inițială configurabilă per echipă

---

## 🔧 Management

```bash
# Status service
sudo systemctl status betfair-bot

# Restart
sudo systemctl restart betfair-bot

# Logs
journalctl -u betfair-bot -f
```

---

## 📞 Info

**VPS:** `89.45.83.59`  
**Dashboard:** `http://89.45.83.59`  
**API:** `http://89.45.83.59/api`

---

**🏆 Gata de Producție!**
