"""Watchlist edge scanning.

Turns a user's tracked players into actionable alerts: for each tracked
player+stat, pull the live line, compare it to the season average, and flag
the ones with an edge right now. `edge_verdict` is pure for unit testing;
`scan_item` does the live fetches.
"""

from src.props import get_full_game_log, stat_value, DEFAULT_SEASON
from src.odds import get_player_line
from src.defense import get_matchup

EDGE_THRESHOLD = 1.5  # |season avg - line| at/above this is flagged as an edge


def edge_verdict(season_avg: float, line: float, threshold: float = EDGE_THRESHOLD) -> dict:
    """Compare a season average to a line. Pure."""
    diff = round(season_avg - line, 1)
    side = "OVER" if diff > 0 else "UNDER" if diff < 0 else "EVEN"
    return {"edge": diff, "side": side, "flagged": abs(diff) >= threshold}


def _season_avg(games: list[dict], stat: str) -> float:
    vals = [stat_value(g, stat) for g in games]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def scan_item(item: dict, season: str = DEFAULT_SEASON) -> dict:
    """Enrich a tracked item with its current live line, edge, and matchup.

    `item` = {id, player_name, player_id, stat}. Returns the item plus
    {available, line, edge, side, flagged, matchup} (available=False if no
    live line right now).
    """
    base = {
        "id": item["id"],
        "player_name": item["player_name"],
        "player_id": item["player_id"],
        "stat": item["stat"],
        "available": False,
    }
    try:
        games = get_full_game_log(item["player_id"], season)
        team = games[0]["team"] if games else ""
        line_info = get_player_line(item["player_name"], item["stat"], team)
        if not line_info or line_info.get("line") is None:
            return base
        avg = _season_avg(games, item["stat"].upper())
        verdict = edge_verdict(avg, line_info["line"])
        matchup = get_matchup(line_info.get("opp"), item["stat"], season) if line_info.get("opp") else None
        return {
            **base,
            "available": True,
            "season_avg": avg,
            "line": line_info["line"],
            "best_over": line_info.get("best_over"),
            "best_under": line_info.get("best_under"),
            "matchup": matchup,
            **verdict,
        }
    except Exception:
        return base
