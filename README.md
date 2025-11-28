# Betfair Bot - Sistem de Pariuri Automate

Bot de pariere automată pe Betfair Exchange cu strategie de progresie pentru recuperarea pierderilor.

## Funcționalități

- **Monitorizare echipe** - Urmărește meciurile echipelor selectate
- **Plasare automată** - Plasează pariuri BACK pe victoria echipei
- **Sistem de progresie** - Calculează miza pentru recuperarea pierderilor
- **Dashboard web** - Interfață pentru control și monitorizare
- **Google Sheets** - Sincronizare date cu spreadsheet

## Structură Proiect

```
/PARIURI
├── backend/                 # Python FastAPI
│   ├── app/
│   │   ├── api/            # REST endpoints
│   │   ├── services/       # Logica de business
│   │   └── models/         # Pydantic schemas
│   └── requirements.txt
│
├── frontend/               # Vue.js Dashboard
│   ├── src/
│   │   ├── views/         # Pagini
│   │   ├── stores/        # Pinia stores
│   │   └── services/      # API client
│   └── package.json
│
└── docker-compose.yml
```

## Instalare

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # sau venv\Scripts\activate pe Windows
pip install -r requirements.txt
cp .env.example .env
# Editează .env cu credențialele tale
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Configurare

### Betfair API

1. Creează cont developer pe [Betfair Developer](https://developer.betfair.com/)
2. Generează App Key
3. Creează certificat SSL pentru autentificare
4. Adaugă credențialele în `.env`

### Google Sheets

1. Creează proiect în [Google Cloud Console](https://console.cloud.google.com/)
2. Activează Google Sheets API
3. Creează Service Account și descarcă JSON
4. Partajează spreadsheet-ul cu email-ul Service Account

## Formula de Progresie

```
La WIN:  Pierdere_Cumulată = 0, Miză = 100 RON
La LOSE: Miză = (Pierdere_Cumulată / (Cotă - 1)) + 100 RON
```

## API Endpoints

| Endpoint           | Metodă         | Descriere                |
| ------------------ | -------------- | ------------------------ |
| `/api/health`      | GET            | Health check             |
| `/api/stats`       | GET            | Statistici dashboard     |
| `/api/bot/state`   | GET            | Stare bot                |
| `/api/bot/start`   | POST           | Pornește bot             |
| `/api/bot/stop`    | POST           | Oprește bot              |
| `/api/bot/run-now` | POST           | Execută ciclu imediat    |
| `/api/teams`       | GET/POST       | Lista/Creare echipe      |
| `/api/teams/{id}`  | GET/PUT/DELETE | CRUD echipă              |
| `/api/bets`        | GET            | Lista pariuri            |
| `/ws`              | WebSocket      | Actualizări în timp real |

## Licență

Proiect privat - Toate drepturile rezervate
