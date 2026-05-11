"""
Fetches recent Premier League match results from football-data.org
and returns a compact summary string to inject as context.
Results are cached for 30 minutes to avoid hitting rate limits.
"""
import os
import time
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY}

# Simple in-memory cache
_cache: dict = {"data": None, "ts": 0}
CACHE_TTL = 1800  # 30 minutes


def _fetch_recent_pl_matches(days_back: int = 7) -> list[dict]:
    today = datetime.date.today()
    date_from = (today - datetime.timedelta(days=days_back)).isoformat()
    date_to = today.isoformat()

    url = f"{BASE_URL}/competitions/PL/matches"
    params = {"dateFrom": date_from, "dateTo": date_to, "status": "FINISHED"}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=8)
        resp.raise_for_status()
        return resp.json().get("matches", [])
    except Exception:
        return []


def _fetch_upcoming_pl_matches(days_ahead: int = 3) -> list[dict]:
    today = datetime.date.today()
    date_from = today.isoformat()
    date_to = (today + datetime.timedelta(days=days_ahead)).isoformat()

    url = f"{BASE_URL}/competitions/PL/matches"
    params = {"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED,TIMED"}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=8)
        resp.raise_for_status()
        return resp.json().get("matches", [])
    except Exception:
        return []


def get_football_context() -> str:
    """
    Returns a brief text summary of recent and upcoming PL matches
    to inject as context into the chat prompt.
    Cached for 30 minutes.
    """
    if not FOOTBALL_API_KEY:
        return ""

    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    lines = [f"TODAY'S DATE: {datetime.date.today().strftime('%A, %d %B %Y')}"]
    lines.append("")
    lines.append("RECENT PREMIER LEAGUE RESULTS (last 7 days):")

    recent = _fetch_recent_pl_matches(7)
    if recent:
        for m in recent:
            home = m["homeTeam"]["shortName"]
            away = m["awayTeam"]["shortName"]
            hg = m["score"]["fullTime"]["home"]
            ag = m["score"]["fullTime"]["away"]
            date = m["utcDate"][:10]
            lines.append(f"  {date}: {home} {hg}-{ag} {away}")
    else:
        lines.append("  (no recent results available)")

    lines.append("")
    lines.append("UPCOMING PREMIER LEAGUE FIXTURES (next 3 days):")

    upcoming = _fetch_upcoming_pl_matches(3)
    if upcoming:
        for m in upcoming:
            home = m["homeTeam"]["shortName"]
            away = m["awayTeam"]["shortName"]
            date = m["utcDate"][:10]
            lines.append(f"  {date}: {home} vs {away}")
    else:
        lines.append("  (no upcoming fixtures)")

    result = "\n".join(lines)
    _cache["data"] = result
    _cache["ts"] = now
    return result
