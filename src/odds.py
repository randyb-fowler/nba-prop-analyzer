"""Live sportsbook odds via The Odds API (the-odds-api.com).

Fetches the real player-prop line for an upcoming game so the analyzer can show
the edge between a player's recent form and the book's number. Free-tier
friendly: results are cached, and any failure (no key, no game, network error,
credits exhausted) degrades silently to None.

Pure helpers (`match_event`, `parse_event_odds`) are split out for unit testing
without network access.
"""

import os

import requests

from src.cache import ttl_cache
from src.nba_stats import _normalize
from src.teams import team_name

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_CONFIGURED = bool(ODDS_API_KEY)

BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"

# Our stat keys -> The Odds API player-prop market keys.
MARKET_MAP = {
    "PTS": "player_points",
    "REB": "player_rebounds",
    "AST": "player_assists",
    "STL": "player_steals",
    "BLK": "player_blocks",
    "3PM": "player_threes",
    "TOV": "player_turnovers",
    "PRA": "player_points_rebounds_assists",
    "PR": "player_points_rebounds",
    "PA": "player_points_assists",
    "RA": "player_rebounds_assists",
}


def match_event(events: list[dict], team_full_name: str) -> dict | None:
    """Return the upcoming event involving a team (by full name), or None."""
    target = _normalize(team_full_name)
    for ev in events:
        home = _normalize(ev.get("home_team", ""))
        away = _normalize(ev.get("away_team", ""))
        if target and (target == home or target == away):
            return ev
    return None


def parse_event_odds(data: dict, player_name: str, market_key: str) -> dict | None:
    """Extract a player's line + prices from an event-odds response.

    Walks bookmakers -> markets -> outcomes; matches the player on the
    (normalized) outcome `description`. Returns the first bookmaker that has
    both an Over and a line. Returns None if not found.
    """
    target = _normalize(player_name)
    for book in data.get("bookmakers", []):
        for market in book.get("markets", []):
            if market.get("key") != market_key:
                continue
            over = under = None
            for o in market.get("outcomes", []):
                if _normalize(o.get("description", "")) != target:
                    continue
                side = (o.get("name") or "").lower()
                if side == "over":
                    over = o
                elif side == "under":
                    under = o
            if over and over.get("point") is not None:
                return {
                    "book": book.get("title") or book.get("key"),
                    "line": float(over["point"]),
                    "over_price": over.get("price"),
                    "under_price": under.get("price") if under else None,
                }
    return None


@ttl_cache(600)  # upcoming events change slowly; 10 min keeps credit use low
def get_events() -> list[dict]:
    """List upcoming NBA events (id, teams, commence_time). 1 credit."""
    if not ODDS_CONFIGURED:
        return []
    try:
        resp = requests.get(
            f"{BASE}/events",
            params={"apiKey": ODDS_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        _log_remaining(resp)
        return resp.json()
    except Exception:
        return []


@ttl_cache(600)
def get_player_line(player_name: str, stat: str, team_abbr: str) -> dict | None:
    """Live line for a player's prop in their upcoming game, or None.

    Returns {book, line, over_price, under_price, home, away, commence_time}.
    """
    stat = stat.upper()
    market_key = MARKET_MAP.get(stat)
    if not (ODDS_CONFIGURED and market_key):
        return None

    event = match_event(get_events(), team_name(team_abbr))
    if not event:
        return None

    try:
        resp = requests.get(
            f"{BASE}/events/{event['id']}/odds",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "us",
                "markets": market_key,
                "oddsFormat": "american",
            },
            timeout=10,
        )
        resp.raise_for_status()
        _log_remaining(resp)
        data = resp.json()
    except Exception:
        return None

    line = parse_event_odds(data, player_name, market_key)
    if not line:
        return None

    return {
        **line,
        "home": event.get("home_team"),
        "away": event.get("away_team"),
        "commence_time": event.get("commence_time"),
    }


def _log_remaining(resp) -> None:
    """Surface remaining Odds API credits in the server log."""
    remaining = resp.headers.get("x-requests-remaining")
    if remaining is not None:
        print(f"[odds] requests remaining: {remaining}")
