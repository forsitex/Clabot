import logging
from typing import List, Dict, Any
import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """Ești un expert în pariuri sportive, specializat în analiza meciurilor de fotbal și baschet.
Rolul tău este să ajuți utilizatorul cu:
- Analiză meciuri și pronosticuri
- Evaluarea cotelor și a valorii pariurilor
- Statistici și forme ale echipelor
- Strategii de pariere

Răspunde întotdeauna în limba română.
Fii concis dar informativ.
Oferă analize obiective bazate pe date și statistici.
Nu garanta niciodată rezultate - pariurile implică risc.
Când analizezi un meci, menționează: forma recentă, confruntări directe, absențe importante, motivație."""


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


ai_chat = AIChat()
