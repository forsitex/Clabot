"""
Analiză PROFUNDĂ meci - toate datele disponibile din Betfair API
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.betfair_client import betfair_client


async def deep_analyze_match(search_term):
    """Analiză completă cu TOATE datele disponibile"""

    print(f"🔍 Analiză profundă: {search_term}\n")

    connected = await betfair_client.connect()
    if not connected:
        print("❌ Nu s-a putut conecta")
        return

    print("✅ Conectat!\n")

    # Caută evenimente
    events = await betfair_client.list_events(
        event_type_id="1",
        text_query=search_term
    )

    if not events:
        print(f"❌ Nu s-a găsit: {search_term}")
        return

    event = events[0]
    event_name = event.get("event", {}).get("name", "Unknown")
    event_id = event.get("event", {}).get("id", "")

    print(f"📊 Meci: {event_name}\n")
    print("="*60)

    # 1. MARKET CATALOGUE (detalii piețe)
    print("\n🔍 1. MARKET CATALOGUE (Toate piețele disponibile)\n")

    import httpx

    params = {
        "filter": {
            "eventIds": [event_id]
        },
        "maxResults": "100",
        "marketProjection": [
            "COMPETITION",
            "EVENT",
            "EVENT_TYPE",
            "RUNNER_DESCRIPTION",
            "RUNNER_METADATA",
            "MARKET_START_TIME",
            "MARKET_DESCRIPTION"
        ]
    }

    url = f"{betfair_client.API_URL}/listMarketCatalogue/"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=betfair_client._get_headers(),
            json=params
        )

        if response.status_code == 200:
            markets = response.json()

            print(f"✅ Găsite {len(markets)} piețe:\n")

            for market in markets:
                market_name = market.get("marketName", "Unknown")
                market_id = market.get("marketId", "")
                total_matched = market.get("totalMatched", 0)

                print(f"   📌 {market_name}")
                print(f"      Market ID: {market_id}")
                print(f"      Total Matched: {total_matched:,.0f} RON")

                # Market description
                desc = market.get("description", {})
                if desc:
                    print(f"      Betting Type: {desc.get('bettingType', 'N/A')}")
                    print(f"      Market Type: {desc.get('marketType', 'N/A')}")
                    print(f"      Suspend Time: {desc.get('suspendTime', 'N/A')}")

                print()

    # 2. MARKET BOOK (prețuri și depth complet)
    print("\n🔍 2. MARKET BOOK (Prețuri detaliate)\n")

    # Găsește Match Odds market
    match_odds_market = None
    for market in markets:
        if market.get("marketName") == "Match Odds":
            match_odds_market = market
            break

    if match_odds_market:
        market_id = match_odds_market["marketId"]

        params = {
            "marketIds": [market_id],
            "priceProjection": {
                "priceData": [
                    "EX_BEST_OFFERS",
                    "EX_ALL_OFFERS",
                    "EX_TRADED",
                    "SP_AVAILABLE",
                    "SP_TRADED"
                ],
                "exBestOffersOverrides": {
                    "bestPricesDepth": 5,
                    "rollupModel": "STAKE",
                    "rollupLimit": 10
                },
                "virtualise": True,
                "rolloverStakes": True
            }
        }

        url = f"{betfair_client.API_URL}/listMarketBook/"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=betfair_client._get_headers(),
                json=params
            )

            if response.status_code == 200:
                result = response.json()

                if result and isinstance(result, list):
                    market_book = result[0]

                    print(f"Status: {market_book.get('status', 'N/A')}")
                    print(f"In-play: {market_book.get('inplay', False)}")
                    print(f"Cross matching: {market_book.get('crossMatching', False)}")
                    print(f"Runners voidable: {market_book.get('runnersVoidable', False)}")
                    print(f"Total matched: {market_book.get('totalMatched', 0):,.0f} RON")
                    print(f"Total available: {market_book.get('totalAvailable', 0):,.0f} RON")
                    print(f"Complete: {market_book.get('isMarketDataDelayed', False)}")
                    print(f"Last match time: {market_book.get('lastMatchTime', 'N/A')}")
                    print(f"Bet delay: {market_book.get('betDelay', 0)} seconds")
                    print(f"Version: {market_book.get('version', 'N/A')}\n")

                    # Runners detaliat
                    for runner in market_book.get("runners", []):
                        selection_id = runner.get("selectionId")

                        # Găsește numele
                        runner_name = "Unknown"
                        for r in match_odds_market.get("runners", []):
                            if r.get("selectionId") == selection_id:
                                runner_name = r.get("runnerName", "Unknown")
                                break

                        print(f"   🎯 {runner_name}")
                        print(f"      Selection ID: {selection_id}")
                        print(f"      Status: {runner.get('status', 'N/A')}")
                        print(f"      Last price traded: {runner.get('lastPriceTraded', 'N/A')}")
                        print(f"      Total matched: {runner.get('totalMatched', 0):,.0f} RON")

                        # Exchange prices
                        ex = runner.get("ex", {})

                        # Available to back (depth)
                        back_offers = ex.get("availableToBack", [])
                        if back_offers:
                            print(f"      📊 BACK Offers (depth {len(back_offers)}):")
                            for i, offer in enumerate(back_offers[:5], 1):
                                print(f"         {i}. @ {offer.get('price', 0)} → {offer.get('size', 0):,.0f} RON")

                        # Available to lay (depth)
                        lay_offers = ex.get("availableToLay", [])
                        if lay_offers:
                            print(f"      📊 LAY Offers (depth {len(lay_offers)}):")
                            for i, offer in enumerate(lay_offers[:5], 1):
                                print(f"         {i}. @ {offer.get('price', 0)} → {offer.get('size', 0):,.0f} RON")

                        # Traded volume
                        traded = ex.get("tradedVolume", [])
                        if traded:
                            print(f"      💰 Traded Volume (top {min(5, len(traded))}):")
                            for trade in traded[:5]:
                                print(f"         @ {trade.get('price', 0)} → {trade.get('size', 0):,.0f} RON")

                        # Starting price
                        sp = runner.get("sp", {})
                        if sp:
                            print(f"      🎲 Starting Price:")
                            print(f"         Near: {sp.get('nearPrice', 'N/A')}")
                            print(f"         Far: {sp.get('farPrice', 'N/A')}")
                            print(f"         Back: {sp.get('backStakeTaken', [])}")
                            print(f"         Lay: {sp.get('layLiabilityTaken', [])}")

                        print()

    # 3. CURRENT ORDERS (pariuri active pe acest meci)
    print("\n🔍 3. CURRENT ORDERS (Pariurile tale active)\n")

    params = {
        "marketIds": [market_id] if match_odds_market else []
    }

    url = f"{betfair_client.API_URL}/listCurrentOrders/"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=betfair_client._get_headers(),
            json=params
        )

        if response.status_code == 200:
            result = response.json()
            orders = result.get("currentOrders", [])

            if orders:
                print(f"✅ Ai {len(orders)} pariuri active:\n")
                for order in orders:
                    print(f"   Bet ID: {order.get('betId')}")
                    print(f"   Side: {order.get('side')}")
                    print(f"   Price: {order.get('priceSize', {}).get('price')}")
                    print(f"   Size: {order.get('priceSize', {}).get('size')}")
                    print(f"   Status: {order.get('status')}")
                    print()
            else:
                print("   ℹ️ Nu ai pariuri active pe acest meci\n")

    # 4. ACCOUNT FUNDS
    print("\n🔍 4. ACCOUNT FUNDS (Soldul tău)\n")

    url = f"{betfair_client.API_URL}/getAccountFunds/"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=betfair_client._get_headers(),
            json={}
        )

        if response.status_code == 200:
            result = response.json()

            print(f"   💰 Available: {result.get('availableToBetBalance', 0):,.2f} RON")
            print(f"   💳 Exposure: {result.get('exposure', 0):,.2f} RON")
            print(f"   📊 Retained: {result.get('retainedCommission', 0):,.2f} RON")
            print(f"   💵 Exposure Limit: {result.get('exposureLimit', 0):,.2f} RON")
            print(f"   🎯 Discount Rate: {result.get('discountRate', 0)}%")
            print(f"   📈 Points Balance: {result.get('pointsBalance', 0)}")

    print("\n" + "="*60)
    print("✅ Analiză completă finalizată!")

    await betfair_client.disconnect()


if __name__ == "__main__":
    search = "Hermannstadt"
    if len(sys.argv) > 1:
        search = " ".join(sys.argv[1:])

    asyncio.run(deep_analyze_match(search))
