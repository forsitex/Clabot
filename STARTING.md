# 🚀 STARTING - Ghid de Pornire

## 📋 Cerințe

### Software necesar:

- **Node.js** 18+ (pentru frontend)
- **Python** 3.10+ (pentru backend)

### Conturi necesare:

- **Betfair** - cont cu API activat
- **Google Cloud** - Service Account pentru Google Sheets
- **Railway** (opțional) - pentru deployment

---

## 🔧 Configurare Locală

### 1. Clonează repository-ul

```bash
git clone https://github.com/forsitex/Clabot.git
cd Clabot
```

### 2. Configurează Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Mac/Linux
# sau: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. Configurează Frontend

```bash
cd frontend
npm install
```

### 4. Creează fișierul `.env` în `/backend`

```env
# Betfair API
BETFAIR_APP_KEY=your_app_key
BETFAIR_USERNAME=your_username
BETFAIR_PASSWORD=your_password
BETFAIR_CERT_BASE64=your_cert_base64
BETFAIR_KEY_BASE64=your_key_base64

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_BASE64=your_credentials_base64
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id

# JWT
JWT_SECRET_KEY=your_secret_key

# Bot Settings
BOT_TIMEZONE=Europe/Bucharest
BOT_RUN_HOUR=10
BOT_RUN_MINUTE=0
BOT_INITIAL_STAKE=5
BOT_MAX_PROGRESSION_STEPS=10
```

---

## ▶️ Pornire Aplicație

### Terminal 1 - Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend

```bash
cd frontend
npm run dev
```

### Accesează aplicația:

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## 🔐 Configurare Betfair API

### 1. Creează Application Key

1. Mergi la https://developer.betfair.com
2. Login cu contul Betfair
3. My Apps → Create New App
4. Copiază **App Key**

### 2. Generează Certificate SSL

```bash
# Generează cheie privată
openssl genrsa -out betfair.key 2048

# Generează cerere certificat
openssl req -new -key betfair.key -out betfair.csr

# Upload CSR pe Betfair Developer Portal
# Descarcă certificatul (.crt)
```

### 3. Convertește la Base64

```bash
# Certificat
base64 -i betfair.crt | tr -d '\n' > cert_base64.txt

# Cheie
base64 -i betfair.key | tr -d '\n' > key_base64.txt
```

Copiază conținutul în `.env`:

- `BETFAIR_CERT_BASE64`
- `BETFAIR_KEY_BASE64`

---

## 📊 Configurare Google Sheets

### 1. Creează Service Account

1. Mergi la https://console.cloud.google.com
2. Creează proiect nou
3. APIs & Services → Enable APIs → Google Sheets API
4. Credentials → Create Credentials → Service Account
5. Descarcă JSON key

### 2. Convertește la Base64

```bash
base64 -i service-account.json | tr -d '\n' > google_creds_base64.txt
```

### 3. Creează Spreadsheet

1. Creează un Google Spreadsheet nou
2. Share cu email-ul Service Account (din JSON)
3. Copiază Spreadsheet ID din URL

---

## ✅ Verificare

### Testează conexiunea Betfair:

```bash
curl http://localhost:8000/api/betfair/status
```

### Testează conexiunea Google Sheets:

```bash
curl http://localhost:8000/api/sheets/status
```

---

## 🚀 Deployment Railway

### 1. Conectează repository-ul

1. Mergi la https://railway.app
2. New Project → Deploy from GitHub
3. Selectează repository-ul

### 2. Adaugă Environment Variables

Copiază toate variabilele din `.env` în Railway Settings.

### 3. Deploy

Railway va face build și deploy automat la fiecare push.

---

## 🆘 Troubleshooting

### Eroare: "INVALID_APP_KEY"

- Verifică `BETFAIR_APP_KEY` în `.env`

### Eroare: "Google Sheets not connected"

- Verifică `GOOGLE_SHEETS_CREDENTIALS_BASE64`
- Verifică că Spreadsheet-ul e shared cu Service Account

### Eroare: "Certificate verify failed"

- Regenerează certificatele Betfair
- Verifică că Base64 e corect (fără newlines)

---

## 📅 Data: 28 Noiembrie 2025
