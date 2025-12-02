"""
Analiză piață Betfair - detectare spike-uri volum (smart money)
Rulare: python analyze_market.py
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.betfair_client import betfair_client


async def analyze_market_volume():
    """Analizează volumul pe piețe din ultimele 24h"""

    print("🔍 Conectare la Betfair...")
    connected = await betfair_client.connect()

    if not connected:
        print("❌ Nu s-a putut conecta la Betfair")
        return

    print("✅ Conectat!\n")

    # Găsește evenimente din ultimele 24h
    print("📊 Căutare evenimente din ultimele 24h...")

    events = await betfair_client.list_events(
        event_type_id="1",  # Football
        text_query=None
    )

    print(f"✅ Găsite {len(events)} evenimente\n")

    smart_money_bets = []

    for event in events[:30]:  # Primele 30 pentru analiză
        event_name = event.get("event", {}).get("name", "Unknown")
        event_id = event.get("event", {}).get("id", "")

        print(f"🔍 Analizez: {event_name}")

        # Găsește piețele
        markets = await betfair_client.list_market_catalogue([event_id])

        for market in markets:
            if market.get("marketName") != "Match Odds":
                continue

            market_id = market["marketId"]

            # Obține market book cu TOATE datele
            import httpx

            params = {
                "marketIds": [market_id],
                "priceProjection": {
                    "priceData": [
                        "EX_BEST_OFFERS",
                        "EX_ALL_OFFERS",
                        "EX_TRADED"  # Volumul tranzacționat
                    ],
                    "virtualise": True
                }
            }

            # Request direct
            url = f"{betfair_client.API_URL}/listMarketBook/"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=betfair_client._get_headers(),
                    json=params
                )

                if response.status_code != 200:
                    continue

                result = response.json()

                if not result or not isinstance(result, list):
                    continue

                market_book = result[0]
                total_matched = market_book.get("totalMatched", 0)

                print(f"  💰 Total matched: {total_matched:,.0f} RON")

                # Analizează fiecare runner
                for runner in market_book.get("runners", []):
                    selection_id = runner.get("selectionId")

                    # Găsește numele runner-ului
                    runner_name = "Unknown"
                    for r in market.get("runners", []):
                        if r.get("selectionId") == selection_id:
                            runner_name = r.get("runnerName", "Unknown")
                            break

                    # Volumul tranzacționat per cotă
                    traded_volume = runner.get("ex", {}).get("tradedVolume", [])

                    if not traded_volume:
                        continue

                    # Caută spike-uri (volume mari)
                    for trade in traded_volume:
                        price = trade.get("price", 0)
                        size = trade.get("size", 0)

                        # Spike = volum > 1000 RON la o cotă
                        if size > 1000:
                            smart_money_bets.append({
                                "event": event_name,
                                "market_id": market_id,
                                "runner": runner_name,
                                "price": price,
                                "volume": size,
                                "total_matched": total_matched
                            })

                            print(f"    🎯 SPIKE: {runner_name} @ {price} - {size:,.0f} RON")

        print()

    # Rezumat
    print("\n" + "="*60)
    print("📊 REZUMAT SMART MONEY BETS")
    print("="*60 + "\n")

    if not smart_money_bets:
        print("❌ Nu s-au găsit spike-uri semnificative (>1000 RON)")
    else:
        # Sortează după volum
        smart_money_bets.sort(key=lambda x: x["volume"], reverse=True)

        print(f"✅ Găsite {len(smart_money_bets)} spike-uri:\n")

        for i, bet in enumerate(smart_money_bets[:20], 1):
            print(f"{i}. {bet['event']}")
            print(f"   Runner: {bet['runner']}")
            print(f"   Cotă: {bet['price']}")
            print(f"   Volum: {bet['volume']:,.0f} RON")
            print(f"   Total piață: {bet['total_matched']:,.0f} RON")
            print(f"   % din piață: {(bet['volume']/bet['total_matched']*100):.1f}%")
            print()

    await betfair_client.disconnect()


if __name__ == "__main__":
    asyncio.run(analyze_market_volume())
