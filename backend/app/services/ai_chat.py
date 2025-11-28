import logging
from typing import List, Dict, Any
from datetime import datetime
import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = f"""Ești un expert în pariuri sportive, specializat în analiza meciurilor de fotbal și baschet.

DATA CURENTĂ: {datetime.now().strftime('%d %B %Y')}. Sezonul 2024-2025 este în desfășurare.

Rolul tău este să ajuți utilizatorul cu:
- Analiză meciuri și pronosticuri
- Evaluarea cotelor și a valorii pariurilor
- Statistici și forme ale echipelor
- Strategii de pariere

AI ACCES LA DATE LIVE: Poți accesa date live de pe Betfair Exchange. Când utilizatorul întreabă despre meciuri, vei primi automat lista de meciuri disponibile cu cote live.

Răspunde întotdeauna în limba română.
Fii concis dar informativ.
Oferă analize obiective bazate pe date și statistici.
Nu garanta niciodată rezultate - pariurile implică risc.
Când analizezi un meci, menționează: forma recentă, confruntări directe, absențe importante, motivație.

Când primești date live de la Betfair, folosește-le pentru a oferi analize actualizate cu cotele reale."""


class AIChat:
    def __init__(self):
        self._client = None
        self._conversation_history: List[Dict[str, str]] = []

    def _get_client(self) -> anthropic.Anthropic:
        if not self._client:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def chat(self, message: str) -> str:
        """Trimite un mesaj și primește răspuns de la AI."""
        try:
            client = self._get_client()

            self._conversation_history.append({
                "role": "user",
                "content": message
            })

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=self._conversation_history
            )

            assistant_message = response.content[0].text

            self._conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            if len(self._conversation_history) > 20:
                self._conversation_history = self._conversation_history[-20:]

            return assistant_message

        except Exception as e:
            logger.error(f"Eroare AI chat: {e}")
            return f"Eroare la procesarea mesajului. Încearcă din nou."

    def clear_history(self) -> None:
        """Șterge istoricul conversației."""
        self._conversation_history = []

    async def analyze_match(self, home_team: str, away_team: str, odds: Dict[str, float] = None) -> str:
        """Analizează un meci specific."""
        odds_info = ""
        if odds:
            odds_info = f"\nCote disponibile: Victorie {home_team}: {odds.get('home', 'N/A')}, Egal: {odds.get('draw', 'N/A')}, Victorie {away_team}: {odds.get('away', 'N/A')}"

        prompt = f"""Analizează meciul: {home_team} vs {away_team}{odds_info}

Oferă:
1. Forma recentă a echipelor
2. Confruntări directe
3. Factori cheie pentru acest meci
4. Pronostic recomandat cu explicație"""

        return await self.chat(prompt)

    async def chat_with_context(self, message: str, matches_data: List[Dict[str, Any]] = None) -> str:
        """Chat cu context din Betfair - meciuri și cote live."""
        context = ""

        if matches_data:
            context = "\n\nMECIURI DISPONIBILE PE BETFAIR (date live):\n"
            for match in matches_data[:10]:
                context += f"- {match.get('home_team', 'N/A')} vs {match.get('away_team', 'N/A')}"
                if match.get('home_odds'):
                    context += f" | Cote: 1={match.get('home_odds')}, X={match.get('draw_odds')}, 2={match.get('away_odds')}"
                context += f" | Start: {match.get('start_time', 'N/A')}\n"

        full_message = message
        if context:
            full_message = f"{message}\n{context}"

        return await self.chat(full_message)

    async def fetch_betfair_matches(self, sport: str = "football", search_query: str = None) -> List[Dict[str, Any]]:
        """Preia meciuri live de pe Betfair."""
        from app.services.betfair_client import betfair_client

        matches = []

        try:
            if not betfair_client.is_connected():
                logger.warning("Betfair client not connected, attempting to connect...")
                connected = await betfair_client.connect()
                if not connected:
                    logger.error("Failed to connect to Betfair")
                    return []

            # Get event type ID
            event_type_id = "1" if sport.lower() == "football" else "7522"

            # List events
            events = await betfair_client.list_events(
                event_type_id=event_type_id,
                text_query=search_query
            )

            if not events:
                return []

            # Get event IDs
            event_ids = [e.get("event", {}).get("id") for e in events[:20] if e.get("event")]

            if not event_ids:
                return []

            # Get market catalogue
            markets = await betfair_client.list_market_catalogue(event_ids)

            if not markets:
                return []

            # Get market IDs for prices
            market_ids = [m.get("marketId") for m in markets[:20] if m.get("marketId")]

            # Get prices
            market_books = await betfair_client.list_market_book(market_ids) if market_ids else []

            # Build price lookup
            price_lookup = {}
            for book in market_books:
                market_id = book.get("marketId")
                runners = book.get("runners", [])
                if len(runners) >= 2:
                    prices = {}
                    for runner in runners:
                        back_prices = runner.get("ex", {}).get("availableToBack", [])
                        if back_prices:
                            prices[runner.get("selectionId")] = back_prices[0].get("price", 0)
                    price_lookup[market_id] = prices

            # Combine data
            for market in markets:
                event = market.get("event", {})
                runners = market.get("runners", [])
                market_id = market.get("marketId")

                if len(runners) >= 2:
                    match_data = {
                        "event_id": event.get("id"),
                        "event_name": event.get("name", ""),
                        "competition": market.get("competition", {}).get("name", ""),
                        "start_time": market.get("marketStartTime", ""),
                        "market_id": market_id,
                        "home_team": runners[0].get("runnerName", ""),
                        "away_team": runners[1].get("runnerName", "") if len(runners) > 1 else "",
                    }

                    # Add prices if available
                    if market_id in price_lookup:
                        prices = price_lookup[market_id]
                        for i, runner in enumerate(runners[:3]):
                            selection_id = runner.get("selectionId")
                            if selection_id in prices:
                                if i == 0:
                                    match_data["home_odds"] = prices[selection_id]
                                elif i == 1:
                                    match_data["away_odds"] = prices[selection_id]
                                elif i == 2:
                                    match_data["draw_odds"] = prices[selection_id]

                    matches.append(match_data)

            logger.info(f"Fetched {len(matches)} matches from Betfair")
            return matches

        except Exception as e:
            logger.error(f"Error fetching Betfair matches: {e}")
            return []

    async def chat_with_betfair(self, message: str, fetch_matches: bool = True) -> str:
        """Chat cu date live de pe Betfair."""
        matches_data = []

        if fetch_matches:
            # Detect if user is asking about specific sport or team
            message_lower = message.lower()
            sport = "football"
            search_query = None

            if "baschet" in message_lower or "basketball" in message_lower or "nba" in message_lower:
                sport = "basketball"

            # Try to extract team name for search
            keywords_to_remove = ["analizeaza", "analizează", "meci", "meciuri", "azi", "maine",
                                  "fotbal", "baschet", "cote", "pariere", "ce", "care", "sunt",
                                  "urmatoarele", "următoarele", "lui", "echipa", "echipei"]
            words = message_lower.split()
            potential_teams = [w for w in words if w not in keywords_to_remove and len(w) > 3]
            if potential_teams:
                search_query = potential_teams[0]

            logger.info(f"Fetching Betfair matches - sport: {sport}, search: {search_query}")
            matches_data = await self.fetch_betfair_matches(sport=sport, search_query=search_query)
            logger.info(f"Got {len(matches_data)} matches from Betfair")

        # If no matches found, add explicit warning to context
        if not matches_data:
            no_data_warning = "\n\n⚠️ ATENȚIE: Nu am putut obține date live de pe Betfair. NU INVENTA meciuri sau cote! Spune utilizatorului că nu ai acces la date în acest moment și oferă doar informații generale bazate pe cunoștințele tale."
            return await self.chat(message + no_data_warning)

        return await self.chat_with_context(message, matches_data)

    async def fetch_my_bets(self) -> Dict[str, Any]:
        """Preia pariurile utilizatorului de pe Betfair."""
        from app.services.betfair_client import betfair_client

        try:
            if not betfair_client.is_connected():
                connected = await betfair_client.connect()
                if not connected:
                    return {"error": "Nu m-am putut conecta la Betfair"}

            summary = await betfair_client.get_all_bets_summary()
            return summary

        except Exception as e:
            logger.error(f"Error fetching bets: {e}")
            return {"error": str(e)}

    async def chat_with_bets(self, message: str) -> str:
        """Chat cu informații despre pariurile utilizatorului."""
        message_lower = message.lower()

        # Check if user is asking about their bets
        bet_keywords = ["pariuri", "pariu", "pariat", "plasate", "active", "câștigat", "castigat",
                        "pierdut", "sold", "cont", "bani", "profit", "istoric"]

        is_asking_about_bets = any(kw in message_lower for kw in bet_keywords)

        if is_asking_about_bets:
            bets_data = await self.fetch_my_bets()

            if "error" in bets_data:
                return await self.chat(message + f"\n\n⚠️ Nu am putut accesa pariurile: {bets_data['error']}")

            # Format bets context
            context = "\n\n📊 PARIURILE TALE DIN CONT BETFAIR:\n"
            context += f"- Pariuri active: {bets_data.get('current_count', 0)}\n"
            context += f"- Miză totală activă: {bets_data.get('total_staked_current', 0)} RON\n"
            context += f"- Pariuri finalizate (7 zile): {bets_data.get('settled_count', 0)}\n"
            context += f"- Câștigate: {bets_data.get('won_count', 0)}\n"
            context += f"- Pierdute: {bets_data.get('lost_count', 0)}\n"
            context += f"- Profit total: {bets_data.get('total_profit', 0)} RON\n"

            # Add current bets details
            current_bets = bets_data.get('current_bets', [])
            if current_bets:
                context += "\nPariuri active:\n"
                for bet in current_bets[:5]:
                    context += f"  • {bet.get('marketId', 'N/A')} - Miză: {bet.get('sizeMatched', 0)} @ {bet.get('averagePriceMatched', 0)}\n"

            return await self.chat(message + context)

        # If not asking about bets, use normal flow
        return await self.chat_with_betfair(message)


ai_chat = AIChat()
