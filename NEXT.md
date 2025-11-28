# 🚀 NEXT - Funcționalități de Implementat

## 🔴 PRIORITATE ÎNALTĂ

### 1. Verificare Automată Rezultate

**Descriere:** După finalizarea meciului, botul verifică automat dacă pariul e WIN sau LOSE

**Implementare:**

- La plasare pariu → salvăm `check_time = marketStartTime + 2h15m`
- Scheduler programează verificare la `check_time`
- La verificare:
  - Betfair API: `listClearedOrders` sau `listMarketBook` (status CLOSED)
  - Dacă SETTLED → actualizează WON/LOST în Google Sheets
  - Dacă încă în joc → reprogramează +15 min
- Actualizare progresie echipă:
  - WIN → reset (cumulative_loss = 0, step = 0)
  - LOSE → increment (cumulative_loss += miză, step += 1)

**Fișiere de modificat:**

- `backend/app/services/bot_engine.py` - funcție `check_bet_result()`
- `backend/app/services/google_sheets.py` - `update_team_progression()`
- `backend/app/main.py` - scheduler dinamic per pariu

---

### 2. Salvare Market ID și Selection ID

**Descriere:** Pentru verificare rezultat, avem nevoie de market_id și selection_id

**Implementare:**

- La plasare pariu → salvăm în Google Sheets:
  - `market_id`
  - `selection_id`
  - `bet_id` (de la Betfair)
  - `check_time`

---

### 4. Statistici Avansate

**Descriere:** Dashboard cu statistici detaliate

**Implementare:**

- Profit/Loss per echipă
- Profit/Loss per zi/săptămână/lună
- Win rate per echipă
- Grafice evoluție

---

### 5. Backup & Restore

**Descriere:** Backup automat date și posibilitate restore

**Implementare:**

- Export Google Sheets → JSON
- Import JSON → Google Sheets
- Backup zilnic automat

- ***

## 📅 Data: 28 Noiembrie 2025
