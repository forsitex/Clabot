"""
Analiză meci specific - flux pariuri, cote, volum
Rulare: python analyze_match.py "Hermannstadt v UTA Arad"
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.betfair_client import betfair_client


async def analyze_specific_match(search_term):
    """Analizează un meci specific"""

    print(f"🔍 Căutare meci: {search_term}\n")

    connected = await betfair_client.connect()
    if not connected:
        print("❌ Nu s-a putut conecta la Betfair")
        return

    print("✅ Conectat la Betfair!\n")

    # Caută evenimente
    events = await betfair_client.list_events(
        event_type_id="1",  # Football
        text_query=search_term
    )

    if not events:
        print(f"❌ Nu s-a găsit meciul: {search_term}")
        return

    print(f"✅ Găsite {len(events)} rezultate:\n")

    for idx, event in enumerate(events[:5], 1):
        event_name = event.get("event", {}).get("name", "Unknown")
        event_id = event.get("event", {}).get("id", "")

        print(f"{idx}. {event_name}")
        print(f"   Event ID: {event_id}\n")

        # Găsește piețele
        markets = await betfair_client.list_market_catalogue([event_id])

        for market in markets:
            if market.get("marketName") != "Match Odds":
                continue

            market_id = market["marketId"]
            runners = market.get("runners", [])

            print(f"   📊 Market: {market.get('marketName')}")
            print(f"   Market ID: {market_id}")
            print(f"   Start: {market.get('marketStartTime', 'N/A')}\n")

            # Obține prețuri LIVE
            import httpx

            params = {
                "marketIds": [market_id],
                "priceProjection": {
                    "priceData": [
                        "EX_BEST_OFFERS",
                        "EX_ALL_OFFERS",
                        "EX_TRADED"
                    ],
                    "virtualise": True
                }
            }

            url = f"{betfair_client.API_URL}/listMarketBook/"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=betfair_client._get_headers(),
                    json=params
                )

                if response.status_code != 200:
                    print(f"   ❌ Eroare la citire market book")
                    continue

                result = response.json()

                if not result or not isinstance(result, list):
                    continue

                market_book = result[0]

                # Informații generale
                status = market_book.get("status", "UNKNOWN")
                total_matched = market_book.get("totalMatched", 0)

                print(f"   📈 Status: {status}")
                print(f"   💰 Total Matched: {total_matched:,.0f} RON")
                print(f"   📊 Lichiditate: {'MARE' if total_matched > 50000 else 'MEDIE' if total_matched > 10000 else 'MICĂ'}\n")

                # Analizează fiecare runner
                print("   🎯 COTE ȘI FLUX:\n")

                for runner in market_book.get("runners", []):
                    selection_id = runner.get("selectionId")

                    # Găsește numele
                    runner_name = "Unknown"
                    for r in runners:
                        if r.get("selectionId") == selection_id:
                            runner_name = r.get("runnerName", "Unknown")
                            break

                    # Best prices
                    ex = runner.get("ex", {})
                    best_back = ex.get("availableToBack", [])
                    best_lay = ex.get("availableToLay", [])

                    back_price = best_back[0].get("price", 0) if best_back else 0
                    back_size = best_back[0].get("size", 0) if best_back else 0

                    lay_price = best_lay[0].get("price", 0) if best_lay else 0
                    lay_size = best_lay[0].get("size", 0) if best_lay else 0

                    # Spread
                    spread = lay_price - back_price if back_price and lay_price else 0

                    print(f"   📌 {runner_name}")
                    print(f"      BACK: {back_price} ({back_size:,.0f} RON disponibil)")
                    print(f"      LAY:  {lay_price} ({lay_size:,.0f} RON disponibil)")
                    print(f"      Spread: {spread:.3f}")

                    # Traded volume
                    traded_volume = ex.get("tradedVolume", [])

                    if traded_volume:
                        print(f"      📊 Volume tranzacționate:")
                        for trade in traded_volume[:5]:  # Top 5
                            print(f"         @ {trade.get('price', 0)} → {trade.get('size', 0):,.0f} RON")

                    # All offers (depth)
                    all_back = ex.get("availableToBack", [])
                    all_lay = ex.get("availableToLay", [])

                    if len(all_back) > 1:
                        print(f"      📊 Depth BACK:")
                        for offer in all_back[:3]:
                            print(f"         @ {offer.get('price', 0)} → {offer.get('size', 0):,.0f} RON")

                    if len(all_lay) > 1:
                        print(f"      📊 Depth LAY:")
                        for offer in all_lay[:3]:
                            print(f"         @ {offer.get('price', 0)} → {offer.get('size', 0):,.0f} RON")

                    print()

                # Analiză flux
                print("   🔍 ANALIZĂ FLUX:\n")

                # Compară volume
                runners_data = []
                for runner in market_book.get("runners", []):
                    selection_id = runner.get("selectionId")
                    runner_name = "Unknown"
                    for r in runners:
                        if r.get("selectionId") == selection_id:
                            runner_name = r.get("runnerName", "Unknown")
                            break

                    ex = runner.get("ex", {})
                    back_size = ex.get("availableToBack", [{}])[0].get("size", 0)
                    lay_size = ex.get("availableToLay", [{}])[0].get("size", 0)

                    runners_data.append({
                        "name": runner_name,
                        "back_size": back_size,
                        "lay_size": lay_size,
                        "total": back_size + lay_size
                    })

                # Sortează după total
                runners_data.sort(key=lambda x: x["total"], reverse=True)

                print("   💰 Lichiditate per runner:")
                for rd in runners_data:
                    print(f"      {rd['name']}: {rd['total']:,.0f} RON")
                    if rd['back_size'] > rd['lay_size'] * 1.5:
                        print(f"         ⚠️ Mai mult BACK = presiune cumpărare")
                    elif rd['lay_size'] > rd['back_size'] * 1.5:
                        print(f"         ⚠️ Mai mult LAY = presiune vânzare")

                print()

    await betfair_client.disconnect()


if __name__ == "__main__":
    search = "Hermannstadt"
    if len(sys.argv) > 1:
        search = " ".join(sys.argv[1:])

    asyncio.run(analyze_specific_match(search))
