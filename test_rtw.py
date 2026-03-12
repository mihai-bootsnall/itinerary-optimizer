"""Quick smoke test: 16-leg round-the-world itinerary."""
import asyncio
import sys
import time

sys.path.insert(0, "/var/www/itinerary-optimizer")

from app.agent import split_itinerary  # noqa: E402
from app.models import ItineraryRequest  # noqa: E402

RTW_REQUEST = {
    "legs": [
        {"origin": "LHR", "destination": "JFK", "departure_date": "2026-05-01"},
        {"origin": "JFK", "destination": "MIA", "departure_date": "2026-05-04"},
        {"origin": "MIA", "destination": "BOG", "departure_date": "2026-05-07"},
        {"origin": "BOG", "destination": "LIM", "departure_date": "2026-05-10"},
        {"origin": "LIM", "destination": "SCL", "departure_date": "2026-05-13"},
        {"origin": "SCL", "destination": "AKL", "departure_date": "2026-05-16"},
        {"origin": "AKL", "destination": "SYD", "departure_date": "2026-05-20"},
        {"origin": "SYD", "destination": "SIN", "departure_date": "2026-05-24"},
        {"origin": "SIN", "destination": "BKK", "departure_date": "2026-05-28"},
        {"origin": "BKK", "destination": "HAN", "departure_date": "2026-05-31"},
        {"origin": "HAN", "destination": "HKG", "departure_date": "2026-06-03"},
        {"origin": "HKG", "destination": "NRT", "departure_date": "2026-06-06"},
        {"origin": "NRT", "destination": "DXB", "departure_date": "2026-06-10"},
        {"origin": "DXB", "destination": "IST", "departure_date": "2026-06-14"},
        {"origin": "IST", "destination": "ATH", "departure_date": "2026-06-17"},
        {"origin": "ATH", "destination": "LHR", "departure_date": "2026-06-20"},
    ],
    "settings": {
        "cabin_class": "C",
        "passengers": [{"type": "ADT", "count": 1}],
        "preferred_airlines": ["*A"],
    },
    "verbose": True,
}


async def main():
    request = ItineraryRequest(**RTW_REQUEST)
    print(f"Sending {len(request.legs)}-leg RTW itinerary ({len(request.strategies)} strategies in parallel)...\n")

    t0 = time.time()
    result = await split_itinerary(request)
    elapsed = time.time() - t0

    print(f"Total legs: {result.total_legs}")
    print(f"Strategies returned: {len(result.options)}")
    print(f"Time: {elapsed:.1f}s\n")

    for opt in result.options:
        print(f"=== {opt.strategy.value.upper()} ===")
        print(f"  {opt.description}")
        print(f"  Searches: {len(opt.searches)}")
        for i, sg in enumerate(opt.searches, 1):
            legs_str = " -> ".join(f"{l.origin}-{l.destination}" for l in sg.legs)
            note = f" -- {sg.note}" if sg.note else ""
            print(f"    [{i}] {legs_str}  ({len(sg.legs)} legs){note}")
        print()

    if result.raw_reasoning:
        print("--- AI Reasoning ---")
        print(result.raw_reasoning[:800])


asyncio.run(main())
