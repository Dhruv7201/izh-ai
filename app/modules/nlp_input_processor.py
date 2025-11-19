import json
import logging
from typing import Any, Dict, List, Optional

import requests

from app.config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_RESULT = {
    "destination": None,
    "duration_days": None,
    "budget": None,
    "dates": None,
    "trip_type": None,
    "preferences": [],
}

REQUEST_TIMEOUT = 60


def _ollama_url(path: str) -> str:
    base = settings.OLLAMA_BASE_URL.rstrip("/")
    return f"{base}{path}"


def _build_prompt(user_input: str) -> str:
    return (
        "You are an expert travel concierge.\n"
        "Analyze the user's travel request and extract structured trip planning details.\n"
        "Return a JSON object with the following keys:\n"
        "destination (string or null), duration_days (integer or null), budget (string or null),\n"
        "dates (ISO date string YYYY-MM-DD or null), trip_type (string or null),\n"
        "preferences (array of strings, empty array if none).\n"
        "Use null when information is missing. The JSON must not include additional keys.\n"
        f"User input: {user_input}"
    )


def _call_ollama(prompt: str) -> str:
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }
    response = requests.post(
        _ollama_url("/api/generate"),
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            return json.loads(text[start : end + 1])
        raise


def _normalize_preferences(value: Any) -> List[str]:
    if isinstance(value, list):
        items = []
        for item in value:
            if not isinstance(item, str):
                item = str(item)
            item = item.strip()
            if item:
                items.append(item)
        return items
    if isinstance(value, str):
        normalized = [part.strip() for part in value.split(",") if part.strip()]
        return normalized
    return []


def _normalize_result(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    result = DEFAULT_RESULT.copy()
    if not isinstance(raw, dict):
        return result

    destination = raw.get("destination")
    if isinstance(destination, str):
        destination = destination.strip()
        if destination:
            result["destination"] = destination

    duration = raw.get("duration_days")
    if duration is not None and duration != "":
        try:
            result["duration_days"] = int(duration)
        except (TypeError, ValueError):
            pass

    budget = raw.get("budget")
    if isinstance(budget, str):
        budget = budget.strip()
        if budget:
            result["budget"] = budget

    dates = raw.get("dates")
    if isinstance(dates, str):
        dates = dates.strip()
        if dates:
            result["dates"] = dates

    trip_type = raw.get("trip_type")
    if isinstance(trip_type, str):
        trip_type = trip_type.strip()
        if trip_type:
            result["trip_type"] = trip_type

    result["preferences"] = _normalize_preferences(raw.get("preferences"))

    return result


def parse_user_input(user_input: str) -> Dict[str, Any]:
    """Use Ollama to extract structured travel planning metadata."""
    prompt = _build_prompt(user_input)
    try:
        response_text = _call_ollama(prompt)
        raw = _extract_json(response_text)
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.exception("Failed to parse user input with Ollama: %s", exc)
        return DEFAULT_RESULT.copy()

    return _normalize_result(raw)
