# 📊 STRATEGY - Strategia de Pariuri

## 🎯 Obiectiv

Recuperarea pierderilor + profit constant prin progresie matematică pe victorii echipe.

---

## ⚽ Tipul de Pariu

- **Pariu:** Victoria echipei (1 sau 2)
- **Piață Betfair:** MATCH_ODDS
- **Selecție:** Primul runner (echipa gazdă)

---

## 📈 Formula de Progresie

### La primul pariu (sau după WIN):

```
Miză = stake_initial (default: 5 RON)
```

### După LOSE:

```
Miză = (Pierdere_Cumulată / (Cotă_nouă - 1)) + stake_initial
```

### La WIN:

```
Reset: Pierdere_Cumulată = 0, Pas = 0
Profit = Miză × (Cotă - 1)
```

---

## 📋 Exemplu Practic

| Pas | Meci   | Cotă | Miză  | Rezultat | Pierdere Cumulată | Profit/Loss |
| --- | ------ | ---- | ----- | -------- | ----------------- | ----------- |
| 0   | Meci 1 | 1.90 | 5.00  | LOSE     | 5.00              | -5.00       |
| 1   | Meci 2 | 1.80 | 11.25 | LOSE     | 16.25             | -11.25      |
| 2   | Meci 3 | 2.00 | 21.25 | WIN      | 0                 | +21.25      |
| 0   | Meci 4 | 1.85 | 5.00  | WIN      | 0                 | +4.25       |

**Total după 4 meciuri:** -5 - 11.25 + 21.25 + 4.25 = **+9.25 RON**

---

## 🛡️ Stop Loss

- **Max pași progresie:** Configurabil (default: 10)
- **Când se atinge:** Botul NU plasează pariu, echipa e în pauză
- **Scop:** Protecție împotriva seriilor lungi de pierderi

---

## ⚙️ Parametri Configurabili

| Parametru               | Default          | Descriere                                |
| ----------------------- | ---------------- | ---------------------------------------- |
| `initial_stake`         | 5 RON            | Miza de bază                             |
| `max_progression_steps` | 10               | Număr maxim de pași înainte de stop loss |
| `bot_run_hour`          | 10               | Ora la care rulează botul                |
| `bot_run_minute`        | 0                | Minutul la care rulează botul            |
| `bot_timezone`          | Europe/Bucharest | Fusul orar                               |

---

## 🔄 Flow Zilnic

```
1. [Ora configurată] Bot pornește automat
2. Citește echipele active din Google Sheets
3. Pentru fiecare echipă:
   - Verifică meciurile de azi
   - Calculează miza bazată pe progresie
   - Plasează pariul pe Betfair
   - Actualizează Google Sheets (status: PENDING)
4. [La fiecare 30 min] Verifică rezultatele
5. La meci terminat:
   - WIN → Reset progresie, marchează profit
   - LOSE → Incrementează progresie
```

---

## 📊 Matematica din Spate

### De ce funcționează formula:

La WIN, câștigul trebuie să acopere:

- Toate pierderile anterioare (Pierdere_Cumulată)
- Plus profitul dorit (stake_initial)

```
Câștig = Miză × (Cotă - 1)
Câștig = Pierdere_Cumulată + stake_initial

=> Miză × (Cotă - 1) = Pierdere_Cumulată + stake_initial
=> Miză = (Pierdere_Cumulată + stake_initial) / (Cotă - 1)
=> Miză = Pierdere_Cumulată / (Cotă - 1) + stake_initial / (Cotă - 1)

Simplificat: Miză ≈ (Pierdere_Cumulată / (Cotă - 1)) + stake_initial
```

---

## ⚠️ Riscuri

1. **Serie lungă de pierderi** → Mize foarte mari
2. **Cotă mică** → Miză mare pentru aceeași recuperare
3. **Fonduri insuficiente** → Nu poți continua progresia

---

## ✅ Avantaje

1. **Profit garantat la WIN** (dacă ai fonduri)
2. **Automatizat complet**
3. **Progresie per echipă** (independent)
4. **Stop loss** pentru protecție

---

## 📅 Data: 28 Noiembrie 2025
