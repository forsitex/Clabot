import logging
import httpx
import os
import base64
import tempfile
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.models.schemas import Match, PlaceOrderResponse

logger = logging.getLogger(__name__)


class BetfairClient:
    """
    Client pentru Betfair Exchange API-NG.
    Gestionează autentificarea, căutarea meciurilor și plasarea pariurilor.
    """

    # Use .ro endpoints for Romanian accounts
    IDENTITY_URL = "https://identitysso-cert.betfair.ro/api/certlogin"
    API_URL = "https://api.betfair.ro/exchange/betting/rest/v1.0"

    # Fallback to global endpoints
    IDENTITY_URL_GLOBAL = "https://identitysso-cert.betfair.com/api/certlogin"
    API_URL_GLOBAL = "https://api.betfair.com/exchange/betting/rest/v1.0"

    FOOTBALL_EVENT_TYPE_ID = "1"
    BASKETBALL_EVENT_TYPE_ID = "7522"

    def __init__(self):
        self._app_key: Optional[str] = None
        self._session_token: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._cert_path: Optional[str] = None
        self._key_path: Optional[str] = None
        self._temp_cert_file: Optional[str] = None
        self._temp_key_file: Optional[str] = None
        self._connected = False
        self._http_client: Optional[httpx.AsyncClient] = None

    def configure(
        self,
        app_key: str,
        username: str,
        password: str,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None
    ) -> bool:
        """
        Configurează clientul Betfair.

        Args:
            app_key: Betfair Application Key
            username: Betfair username
            password: Betfair password
            cert_path: Calea către certificatul SSL
            key_path: Calea către cheia SSL

        Returns:
            True dacă configurarea a reușit
        """
        self._app_key = app_key
        self._username = username
        self._password = password
        self._cert_path = cert_path
        self._key_path = key_path

        # Check for base64 encoded certificates in environment
        cert_base64 = os.environ.get("BETFAIR_CERT_BASE64")
        key_base64 = os.environ.get("BETFAIR_KEY_BASE64")

        if cert_base64 and key_base64:
            try:
                # Create temporary files for certificates
                cert_data = base64.b64decode(cert_base64)
                key_data = base64.b64decode(key_base64)

                # Write to temp files
                cert_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.crt', delete=False)
                cert_file.write(cert_data)
                cert_file.close()
                self._temp_cert_file = cert_file.name
                self._cert_path = cert_file.name

                key_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False)
                key_file.write(key_data)
                key_file.close()
                self._temp_key_file = key_file.name
                self._key_path = key_file.name

                logger.info("Certificate loaded from environment variables")
            except Exception as e:
                logger.error(f"Failed to load certificates from env: {e}")

        return True

    async def connect(self) -> bool:
        """
        Autentifică la Betfair API.

        Returns:
            True dacă autentificarea a reușit
        """
        if not all([self._app_key, self._username, self._password]):
            logger.error("Credențiale Betfair incomplete")
            return False

        try:
            cert = None
            if self._cert_path and self._key_path:
                cert = (self._cert_path, self._key_path)

            # Check for proxy configuration
            proxy_url = os.environ.get("BETFAIR_PROXY_URL")
            proxies = proxy_url if proxy_url else None

            if proxies:
                logger.info(f"Using proxy: {proxy_url}")

            async with httpx.AsyncClient(cert=cert, proxy=proxies) as client:
                response = await client.post(
                    self.IDENTITY_URL,
                    headers={"X-Application": self._app_key},
                    data={
                        "username": self._username,
                        "password": self._password
                    }
                )

                result = response.json()

                if result.get("loginStatus") == "SUCCESS":
                    self._session_token = result.get("sessionToken")
                    self._connected = True
                    # Store proxy for future requests
                    self._proxy_url = proxies
                    self._http_client = httpx.AsyncClient(proxy=proxies)
                    logger.info("Autentificat la Betfair API")
                    return True
                else:
                    logger.error(f"Autentificare eșuată: {result.get('loginStatus')}")
                    return False

        except Exception as e:
            logger.error(f"Eroare la autentificarea Betfair: {e}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Verifică dacă clientul este conectat."""
        return self._connected and self._session_token is not None

    async def disconnect(self) -> None:
        """Deconectează clientul."""
        if self._http_client:
            await self._http_client.aclose()
        self._session_token = None
        self._connected = False

        # Cleanup temp certificate files
        if self._temp_cert_file and os.path.exists(self._temp_cert_file):
            os.unlink(self._temp_cert_file)
        if self._temp_key_file and os.path.exists(self._temp_key_file):
            os.unlink(self._temp_key_file)

        logger.info("Deconectat de la Betfair API")

    def _get_headers(self) -> Dict[str, str]:
        """Returnează headerele pentru request-uri API."""
        return {
            "X-Application": self._app_key or "",
            "X-Authentication": self._session_token or "",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execută un request către Betfair API.

        Args:
            endpoint: Endpoint-ul API (ex: listMarketCatalogue)
            params: Parametrii request-ului

        Returns:
            Răspunsul API ca dicționar
        """
        if not self.is_connected():
            raise Exception("Nu sunt conectat la Betfair API")

        url = f"{self.API_URL}/{endpoint}/"

        try:
            response = await self._http_client.post(
                url,
                headers=self._get_headers(),
                json=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Eroare API: {response.status_code} - {response.text}")
                return {"error": response.text}

        except Exception as e:
            logger.error(f"Eroare request API: {e}")
            return {"error": str(e)}

    async def list_events(
        self,
        event_type_id: str,
        competition_ids: Optional[List[str]] = None,
        text_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Listează evenimentele disponibile.

        Args:
            event_type_id: ID-ul tipului de eveniment (1=Football)
            competition_ids: Lista de ID-uri competiții (opțional)
            text_query: Căutare text (opțional)

        Returns:
            Lista de evenimente
        """
        market_filter = {
            "eventTypeIds": [event_type_id],
            "marketStartTime": {
                "from": datetime.utcnow().isoformat() + "Z",
                "to": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
            }
        }

        if competition_ids:
            market_filter["competitionIds"] = competition_ids

        if text_query:
            market_filter["textQuery"] = text_query

        result = await self._api_request("listEvents", {"filter": market_filter})

        if "error" in result:
            return []

        return result if isinstance(result, list) else []

    async def list_market_catalogue(
        self,
        event_ids: List[str],
        market_type_codes: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Listează piețele pentru evenimente.

        Args:
            event_ids: Lista de ID-uri evenimente
            market_type_codes: Tipuri de piețe (default: MATCH_ODDS)

        Returns:
            Lista de piețe
        """
        if market_type_codes is None:
            market_type_codes = ["MATCH_ODDS"]

        params = {
            "filter": {
                "eventIds": event_ids,
                "marketTypeCodes": market_type_codes
            },
            "maxResults": "100",
            "marketProjection": [
                "COMPETITION",
                "EVENT",
                "EVENT_TYPE",
                "RUNNER_DESCRIPTION",
                "MARKET_START_TIME"
            ]
        }

        result = await self._api_request("listMarketCatalogue", params)

        if "error" in result:
            return []

        return result if isinstance(result, list) else []

    async def list_market_book(self, market_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Obține prețurile pentru piețe.

        Args:
            market_ids: Lista de ID-uri piețe

        Returns:
            Lista de market books cu prețuri
        """
        params = {
            "marketIds": market_ids,
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS"],
                "virtualise": True
            }
        }

        result = await self._api_request("listMarketBook", params)

        if "error" in result:
            return []

        return result if isinstance(result, list) else []

    async def find_matches_for_team(self, team) -> List[Match]:
        """
        Caută meciuri pentru o echipă.

        Args:
            team: Obiectul Team

        Returns:
            Lista de meciuri găsite
        """
        event_type_id = (
            self.FOOTBALL_EVENT_TYPE_ID
            if team.sport == "football"
            else self.BASKETBALL_EVENT_TYPE_ID
        )

        events = await self.list_events(
            event_type_id=event_type_id,
            text_query=team.name
        )

        if not events:
            return []

        event_ids = [e["event"]["id"] for e in events[:5]]

        markets = await self.list_market_catalogue(event_ids)

        if not markets:
            return []

        market_ids = [m["marketId"] for m in markets]
        market_books = await self.list_market_book(market_ids)

        market_prices = {mb["marketId"]: mb for mb in market_books}

        matches = []
        for market in markets:
            if market.get("marketName") != "Match Odds":
                continue

            event = market.get("event", {})
            competition = market.get("competition", {})
            runners = market.get("runners", [])

            if len(runners) < 3:
                continue

            market_book = market_prices.get(market["marketId"], {})
            runner_prices = {
                r["selectionId"]: r
                for r in market_book.get("runners", [])
            }

            home_runner = runners[0]
            away_runner = runners[1]
            draw_runner = runners[2]

            def get_back_price(selection_id: int) -> Optional[float]:
                runner = runner_prices.get(selection_id, {})
                back_prices = runner.get("ex", {}).get("availableToBack", [])
                if back_prices:
                    return back_prices[0].get("price")
                return None

            match = Match(
                event_id=event.get("id", ""),
                event_name=event.get("name", ""),
                market_id=market["marketId"],
                competition_id=competition.get("id", ""),
                competition_name=competition.get("name", ""),
                start_time=datetime.fromisoformat(
                    market.get("marketStartTime", "").replace("Z", "+00:00")
                ),
                home_team=home_runner.get("runnerName", ""),
                away_team=away_runner.get("runnerName", ""),
                home_selection_id=str(home_runner.get("selectionId", "")),
                away_selection_id=str(away_runner.get("selectionId", "")),
                draw_selection_id=str(draw_runner.get("selectionId", "")),
                home_odds=get_back_price(home_runner.get("selectionId")),
                away_odds=get_back_price(away_runner.get("selectionId")),
                draw_odds=get_back_price(draw_runner.get("selectionId")),
                total_matched=market_book.get("totalMatched", 0)
            )

            matches.append(match)

        return matches

    async def place_bet(
        self,
        market_id: str,
        selection_id: str,
        stake: float,
        odds: float,
        side: str = "BACK"
    ) -> PlaceOrderResponse:
        """
        Plasează un pariu pe Betfair.

        Args:
            market_id: ID-ul pieței
            selection_id: ID-ul selecției
            stake: Miza în RON
            odds: Cota
            side: BACK sau LAY

        Returns:
            Răspunsul plasării
        """
        params = {
            "marketId": market_id,
            "instructions": [{
                "selectionId": selection_id,
                "handicap": "0",
                "side": side,
                "orderType": "LIMIT",
                "limitOrder": {
                    "size": str(round(stake, 2)),
                    "price": str(odds),
                    "persistenceType": "LAPSE"
                }
            }]
        }

        result = await self._api_request("placeOrders", params)

        if "error" in result:
            return PlaceOrderResponse(
                success=False,
                status="ERROR",
                error_message=result.get("error", "Unknown error")
            )

        status = result.get("status", "FAILURE")
        instruction_reports = result.get("instructionReports", [])

        if status == "SUCCESS" and instruction_reports:
            report = instruction_reports[0]
            return PlaceOrderResponse(
                success=True,
                bet_id=report.get("betId"),
                status=report.get("status", "SUCCESS"),
                size_matched=report.get("sizeMatched", 0),
                average_price_matched=report.get("averagePriceMatched", 0),
                placed_date=datetime.fromisoformat(
                    report.get("placedDate", "").replace("Z", "+00:00")
                ) if report.get("placedDate") else None
            )
        else:
            error_code = result.get("errorCode", "UNKNOWN")
            return PlaceOrderResponse(
                success=False,
                status="FAILURE",
                error_code=error_code,
                error_message=f"Plasare eșuată: {error_code}"
            )

    async def get_account_funds(self) -> Dict[str, Any]:
        """Obține fondurile din cont."""
        result = await self._api_request("getAccountFunds", {})
        return result


betfair_client = BetfairClient()

# Auto-configure from environment variables at startup
def auto_configure_betfair():
    """Auto-configure Betfair client from environment variables."""
    from app.config import get_settings
    settings = get_settings()

    if settings.betfair_app_key and settings.betfair_username and settings.betfair_password:
        betfair_client.configure(
            app_key=settings.betfair_app_key,
            username=settings.betfair_username,
            password=settings.betfair_password,
            cert_path=settings.betfair_cert_path,
            key_path=settings.betfair_key_path
        )
        logger.info("Betfair client auto-configured from environment variables")
    else:
        logger.warning("Betfair credentials not found in environment variables")

# Run auto-configure
auto_configure_betfair()
