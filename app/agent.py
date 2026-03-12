from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)
from app.models import (
    ItineraryRequest,
    ItineraryResponse,
    Leg,
    SearchGroup,
    SplitOption,
    Strategy,
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Map compact AI output keys → Leg field names
_LEG_KEY_MAP = {
    "from": "origin",
    "to": "destination",
    "date": "date",
    "cabin": "cabin_class",
    "flex": "flexible_date",
    "apt_chg": "allow_airport_change",
    "nearby": "allow_nearby_locations",
    "pref": "preferred_airlines",
    "excl": "excluded_airlines",
    "surface": "surface_segment",
}


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def _build_user_prompt(request: ItineraryRequest, strategy: Strategy) -> str:
    legs_desc = []
    for i, leg in enumerate(request.legs, 1):
        parts = [
            f"Leg {i}: {leg.origin}→{leg.destination} {leg.date}",
        ]
        if leg.surface_segment:
            parts.append(" [SURFACE]")
        if leg.cabin_class:
            parts.append(f" cabin={leg.cabin_class.value}")
        if leg.flexible_date is not None:
            parts.append(f" flex={leg.flexible_date}")
        if leg.allow_airport_change is not None:
            parts.append(f" apt_chg={leg.allow_airport_change}")
        if leg.allow_nearby_locations is not None:
            parts.append(f" nearby={leg.allow_nearby_locations}")
        if leg.preferred_airlines:
            parts.append(f" pref={','.join(leg.preferred_airlines)}")
        if leg.excluded_airlines:
            parts.append(f" excl={','.join(leg.excluded_airlines)}")
        legs_desc.append("".join(parts))

    s = request.settings
    global_parts = [
        f"cabin={s.cabin_class.value}",
        f"flex={s.flexible_date}",
        f"apt_chg={s.allow_airport_change}",
        f"nearby={s.allow_nearby_locations}",
    ]
    if s.preferred_airlines:
        global_parts.append(f"pref={','.join(s.preferred_airlines)}")
    if s.excluded_airlines:
        global_parts.append(f"excl={','.join(s.excluded_airlines)}")
    pax_parts = [f"{p.count}x{p.type.value}" for p in s.passengers]
    global_parts.append(f"pax={'+'.join(pax_parts)}")

    return (
        f"Itinerary ({len(request.legs)} legs):\n"
        + "\n".join(legs_desc)
        + "\n\nGlobals: " + " ".join(global_parts)
        + f"\n\nProduce the **{strategy.value}** strategy only."
    )


def _expand_leg(compact: dict) -> dict:
    """Map compact AI keys back to full Leg field names."""
    expanded = {}
    for k, v in compact.items():
        full_key = _LEG_KEY_MAP.get(k, k)
        expanded[full_key] = v
    return expanded


def _clean_json(text: str) -> str:
    """Strip markdown fences and fix common LLM JSON issues."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        cleaned = cleaned.strip()
    # Fix trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _parse_single_strategy(
    text: str, strategy: Strategy, verbose: bool,
) -> SplitOption:
    """Parse the AI response for a single strategy."""
    data = json.loads(_clean_json(text))

    searches = []
    for sg in data["searches"]:
        legs = [Leg(**_expand_leg(leg)) for leg in sg["legs"]]
        note = sg.get("note", "") if verbose else ""
        searches.append(SearchGroup(legs=legs, note=note))

    return SplitOption(
        strategy=strategy,
        description=data.get("desc", ""),
        searches=searches,
    )


async def _call_strategy(
    client: anthropic.AsyncAnthropic,
    request: ItineraryRequest,
    strategy: Strategy,
    system_prompt: str,
) -> SplitOption:
    """Make a single AI call for one strategy."""
    user_prompt = _build_user_prompt(request, strategy)

    message = await client.messages.create(
        model=settings.ai_model,
        max_tokens=settings.ai_max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text if message.content else ""

    try:
        option = _parse_single_strategy(response_text, strategy, request.verbose)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error(
            "Strategy %s failed to parse: %s — raw response: %.500s",
            strategy.value, exc, response_text,
        )
        raise ValueError("Optimization request failed, please try again later") from exc

    if request.verbose:
        try:
            data = json.loads(_clean_json(response_text))
            option._reasoning = data.get("reasoning", "")
        except (json.JSONDecodeError, KeyError):
            option._reasoning = ""
    else:
        option._reasoning = ""

    return option


def _resolve_strategies(request: ItineraryRequest) -> list[Strategy]:
    """Determine which strategies to compute.

    If the request explicitly lists strategies, use those.
    Otherwise fall back to ITINERARY_DEFAULT_STRATEGIES from config (comma-separated).
    If that is also empty, return all four strategies.
    """
    # Request provided explicit strategies — use them
    if request.strategies:
        return request.strategies

    # Try config default
    if settings.default_strategies:
        names = [s.strip().lower() for s in settings.default_strategies.split(",") if s.strip()]
        valid = []
        for name in names:
            try:
                valid.append(Strategy(name))
            except ValueError:
                pass
        if valid:
            return valid

    # Fallback: all strategies
    return list(Strategy)


async def split_itinerary(request: ItineraryRequest) -> ItineraryResponse:
    """Call the AI agent to split the itinerary — one call per strategy, in parallel."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    system_prompt = _load_prompt("system.txt")

    strategies = _resolve_strategies(request)
    tasks = [
        _call_strategy(client, request, strategy, system_prompt)
        for strategy in strategies
    ]
    options = await asyncio.gather(*tasks)

    reasoning = ""
    if request.verbose:
        parts = [f"[{o.strategy.value}] {o._reasoning}" for o in options if o._reasoning]
        reasoning = "\n".join(parts)

    return ItineraryResponse(
        options=list(options),
        total_legs=len(request.legs),
        raw_reasoning=reasoning,
    )
