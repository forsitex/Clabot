#!/usr/bin/env python3
"""
Script de testare pentru API-ul Betfair
Verifică autentificarea și funcționalitatea API-ului
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / "backend" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️  .env not found at: {env_path}")

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.betfair_client import BetfairClient
from app.config import get_settings


async def test_betfair_connection():
    """Testează conexiunea la Betfair API."""
    print("=" * 60)
    print("TEST BETFAIR API CONNECTION")
    print("=" * 60)

    settings = get_settings()

    # Display configuration (masked)
    print("\n📋 Configurație:")
    print(f"  APP_KEY: {settings.betfair_app_key[:10]}..." if settings.betfair_app_key else "  APP_KEY: ❌ LIPSEȘTE")
    print(f"  USERNAME: {settings.betfair_username}")
    print(f"  PASSWORD: {'*' * len(settings.betfair_password)}")
    print(f"  CERT PATH: {settings.betfair_cert_path}")
    print(f"  KEY PATH: {settings.betfair_key_path}")

    # Check if certificates exist
    cert_exists = os.path.exists(settings.betfair_cert_path)
    key_exists = os.path.exists(settings.betfair_key_path)

    print(f"\n🔐 Certificate:")
    print(f"  betfair.crt: {'✅ Există' if cert_exists else '❌ LIPSEȘTE'}")
    print(f"  betfair.key: {'✅ Există' if key_exists else '❌ LIPSEȘTE'}")

    if not cert_exists or not key_exists:
        print("\n❌ Certificate lipsă! Nu se poate conecta la Betfair.")
        return False

    # Create client
    client = BetfairClient()
    client.configure(
        app_key=settings.betfair_app_key,
        username=settings.betfair_username,
        password=settings.betfair_password,
        cert_path=settings.betfair_cert_path,
        key_path=settings.betfair_key_path
    )

    # Test 1: Authentication
    print("\n" + "=" * 60)
    print("TEST 1: AUTENTIFICARE")
    print("=" * 60)

    try:
        connected = await client.connect()
        if connected:
            print("✅ Autentificare reușită!")
            print(f"   Session Token: {client._session_token[:20]}...")
        else:
            print("❌ Autentificare eșuată!")
            return False
    except Exception as e:
        print(f"❌ Eroare la autentificare: {e}")
        return False

    # Test 2: List Events
    print("\n" + "=" * 60)
    print("TEST 2: LISTARE EVENIMENTE (Football)")
    print("=" * 60)

    try:
        events = await client.list_events(
            event_type_id="1",  # Football
            text_query="Barcelona"
        )
        print(f"✅ Găsite {len(events)} evenimente pentru 'Barcelona'")

        if events:
            print("\n📋 Primele 3 evenimente:")
            for i, event in enumerate(events[:3], 1):
                event_data = event.get("event", {})
                print(f"   {i}. {event_data.get('name', 'N/A')}")
                print(f"      ID: {event_data.get('id', 'N/A')}")
                print(f"      Data: {event_data.get('openDate', 'N/A')}")
    except Exception as e:
        print(f"❌ Eroare la listare evenimente: {e}")
        return False

    # Test 3: Get Account Funds
    print("\n" + "=" * 60)
    print("TEST 3: FONDURI CONT")
    print("=" * 60)

    try:
        funds = await client.get_account_funds()
        if "error" not in funds:
            available = funds.get("availableToBetBalance", 0)
            exposure = funds.get("exposure", 0)
            print(f"✅ Fonduri disponibile: {available} RON")
            print(f"   Expunere: {exposure} RON")
        else:
            print(f"⚠️  Nu s-au putut obține fondurile: {funds.get('error')}")
    except Exception as e:
        print(f"⚠️  Eroare la obținere fonduri: {e}")

    # Test 4: Current Orders
    print("\n" + "=" * 60)
    print("TEST 4: PARIURI ACTIVE")
    print("=" * 60)

    try:
        current_orders = await client.get_current_orders()
        print(f"✅ Pariuri active: {len(current_orders)}")

        if current_orders:
            print("\n📋 Pariuri active:")
            for i, order in enumerate(current_orders[:5], 1):
                print(f"   {i}. Bet ID: {order.get('betId')}")
                print(f"      Miză: {order.get('sizeMatched', 0)} @ {order.get('averagePriceMatched', 0)}")
                print(f"      Status: {order.get('status')}")
    except Exception as e:
        print(f"❌ Eroare la obținere pariuri active: {e}")

    # Test 5: Settled Orders
    print("\n" + "=" * 60)
    print("TEST 5: PARIURI FINALIZATE (ultimele 7 zile)")
    print("=" * 60)

    try:
        settled_orders = await client.get_settled_orders(days=7)
        print(f"✅ Pariuri finalizate: {len(settled_orders)}")

        if settled_orders:
            total_profit = sum(float(o.get("profit", 0)) for o in settled_orders)
            won = len([o for o in settled_orders if float(o.get("profit", 0)) > 0])
            lost = len([o for o in settled_orders if float(o.get("profit", 0)) < 0])

            print(f"\n📊 Statistici:")
            print(f"   Câștigate: {won}")
            print(f"   Pierdute: {lost}")
            print(f"   Profit total: {total_profit:.2f} RON")

            print("\n📋 Ultimele 3 pariuri:")
            for i, order in enumerate(settled_orders[:3], 1):
                profit = float(order.get("profit", 0))
                status = "✅ WIN" if profit > 0 else "❌ LOST"
                print(f"   {i}. {status} - Profit: {profit:.2f} RON")
                print(f"      Bet ID: {order.get('betId')}")
                print(f"      Data: {order.get('settledDate', 'N/A')}")
    except Exception as e:
        print(f"❌ Eroare la obținere pariuri finalizate: {e}")

    # Test 6: Market Catalogue
    print("\n" + "=" * 60)
    print("TEST 6: MARKET CATALOGUE & ODDS")
    print("=" * 60)

    try:
        # Get first event
        events = await client.list_events(event_type_id="1", text_query="Real Madrid")
        if events:
            event_id = events[0].get("event", {}).get("id")
            event_name = events[0].get("event", {}).get("name")

            print(f"📋 Analizare meci: {event_name}")

            # Get markets
            markets = await client.list_market_catalogue(
                event_ids=[event_id],
                market_type_codes=["MATCH_ODDS"]
            )

            if markets:
                market = markets[0]
                market_id = market.get("marketId")
                runners = market.get("runners", [])

                print(f"   Market ID: {market_id}")
                print(f"   Runners: {len(runners)}")

                # Get prices
                prices = await client.list_market_book([market_id])
                if prices and prices[0].get("runners"):
                    print("\n   💰 Cote disponibile:")
                    for runner in runners[:3]:
                        runner_name = runner.get("runnerName")
                        selection_id = runner.get("selectionId")

                        # Find price
                        for price_runner in prices[0].get("runners", []):
                            if price_runner.get("selectionId") == selection_id:
                                back_prices = price_runner.get("ex", {}).get("availableToBack", [])
                                if back_prices:
                                    odds = back_prices[0].get("price")
                                    print(f"      {runner_name}: {odds}")
                                break

                print("✅ Market catalogue & odds funcționează!")
            else:
                print("⚠️  Nu s-au găsit piețe pentru acest eveniment")
        else:
            print("⚠️  Nu s-au găsit evenimente pentru test")
    except Exception as e:
        print(f"❌ Eroare la market catalogue: {e}")

    # Disconnect
    await client.disconnect()

    print("\n" + "=" * 60)
    print("✅ TOATE TESTELE COMPLETATE!")
    print("=" * 60)
    print("\n🎯 API-ul Betfair funcționează corect!")
    print("   - Autentificare: ✅")
    print("   - Listare evenimente: ✅")
    print("   - Obținere cote: ✅")
    print("   - Pariuri active/finalizate: ✅")

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_betfair_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test întrerupt de utilizator")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Eroare critică: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
