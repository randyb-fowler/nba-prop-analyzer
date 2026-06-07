"""Team injury reports, sourced best-effort from ESPN's public NBA feed.

nba_api does not expose injuries, so this uses ESPN's free injuries endpoint.
It is a third-party source and may change or be unavailable; all failures
degrade gracefully to {"available": False, ...} rather than raising.
"""

import requests

from src.nba_stats import _normalize
from src.teams import team_name

ESPN_INJURIES_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"


def get_team_injuries(team_abbr: str) -> dict:
    """Return current injuries for a team by NBA abbreviation (e.g. 'LAL').

    Shape: {"available": bool, "team": str, "items": [ {player, pos, status,
    detail, return_date, comment} ]}
    """
    full_name = team_name(team_abbr)
    result = {"available": False, "team": full_name, "items": []}

    try:
        resp = requests.get(
            ESPN_INJURIES_URL,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return result  # network/parse failure -> gracefully unavailable

    result["available"] = True
    target = _normalize(full_name)

    for team in data.get("injuries", []):
        if _normalize(team.get("displayName", "")) != target:
            continue
        for inj in team.get("injuries", []):
            athlete = inj.get("athlete", {}) or {}
            details = inj.get("details", {}) or {}
            position = (athlete.get("position", {}) or {}).get("abbreviation", "")
            detail_parts = [p for p in (details.get("side"), details.get("detail")) if p]
            result["items"].append({
                "player": athlete.get("displayName", "Unknown"),
                "pos": position,
                "status": inj.get("status", "Unknown"),
                "detail": " ".join(detail_parts),
                "return_date": details.get("returnDate", ""),
                "comment": inj.get("shortComment", ""),
            })
        break

    return result
