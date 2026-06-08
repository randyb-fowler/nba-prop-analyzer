"""Prop bet / DFS analysis engine.

Given a player, a stat, and a betting line, computes hit rates over recent
windows, home/away splits, optional opponent splits, per-game venue, and a
lean (Over / Under / Pass).

The pure computation lives in `analyze_from_games`, which takes a pre-fetched
game log and hits no network -- this keeps it unit-testable. `analyze_prop`
is the thin wrapper that fetches live data and delegates to it.
"""

from statistics import median

from nba_api.stats.endpoints import playergamelog

from src.cache import ttl_cache
from src.nba_stats import find_player
from src.teams import venue

# Current default season. NBA seasons span two years; update as needed.
DEFAULT_SEASON = "2024-25"

# Seasons offered in the UI dropdown (most recent first).
SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23", "2021-22", "2020-21"]


def supported_seasons() -> list[str]:
    return list(SEASONS)

# Stats the analyzer supports. Combos are computed from base columns.
# label -> list of NBA stat columns to sum.
STAT_DEFINITIONS = {
    "PTS": ["PTS"],
    "REB": ["REB"],
    "AST": ["AST"],
    "STL": ["STL"],
    "BLK": ["BLK"],
    "3PM": ["FG3M"],
    "TOV": ["TOV"],
    "PRA": ["PTS", "REB", "AST"],
    "PR": ["PTS", "REB"],
    "PA": ["PTS", "AST"],
    "RA": ["REB", "AST"],
}


def supported_stats() -> list[str]:
    return list(STAT_DEFINITIONS.keys())


@ttl_cache(3600)  # game logs change at most once a day; 1h is plenty
def get_full_game_log(player_id: int, season: str = DEFAULT_SEASON) -> list[dict]:
    """Return every game this season as enriched rows (most recent first)."""
    log = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season,
        timeout=30,
    )
    df = log.get_data_frames()[0]

    if df.empty:
        raise ValueError("No game log data found for this player/season.")

    rows = []
    for _, row in df.iterrows():
        matchup = row["MATCHUP"]
        is_home = "vs." in matchup
        tokens = matchup.split()
        team_abbr = tokens[0]
        opponent = tokens[-1]
        rows.append({
            "date": row["GAME_DATE"],
            "matchup": matchup,
            "team": team_abbr,
            "is_home": is_home,
            "opponent": opponent,
            "MIN": int(float(row["MIN"])),
            "PTS": int(row["PTS"]),
            "REB": int(row["REB"]),
            "AST": int(row["AST"]),
            "STL": int(row["STL"]),
            "BLK": int(row["BLK"]),
            "FG3M": int(row["FG3M"]),
            "TOV": int(row["TOV"]),
        })
    return rows


def stat_value(game: dict, stat: str) -> int:
    """Compute the value of a (possibly combined) stat for one game."""
    return sum(game[col] for col in STAT_DEFINITIONS[stat])


def _hit_rate(values: list[int], line: float, over: bool) -> dict:
    """Hit rate for a list of stat values against a line."""
    if not values:
        return {"games": 0, "hits": 0, "rate": 0.0, "avg": 0.0}
    hits = sum(1 for v in values if (v > line if over else v < line))
    return {
        "games": len(values),
        "hits": hits,
        "rate": round(100 * hits / len(values), 1),
        "avg": round(sum(values) / len(values), 1),
    }


def _lean(season_rate: float, recent_rate: float, margin: float) -> str:
    """Produce a simple recommendation from hit rates and the avg-vs-line margin."""
    score = (0.6 * recent_rate) + (0.4 * season_rate)
    if score >= 60 and margin > 0:
        return "OVER"
    if score <= 40 and margin < 0:
        return "UNDER"
    return "PASS"


def _host_team(game: dict) -> str:
    """The team whose arena the game was played in."""
    return game["team"] if game["is_home"] else game["opponent"]


def analyze_from_games(player_name: str, player_id, games: list[dict], stat: str,
                       line: float, over: bool = True, season: str = DEFAULT_SEASON,
                       opponent: str | None = None) -> dict:
    """Pure analysis over a pre-fetched game log. No network access."""
    stat = stat.upper()
    if stat not in STAT_DEFINITIONS:
        raise ValueError(f"Unsupported stat '{stat}'. Choose from: {', '.join(supported_stats())}")

    valued = [{**g, "value": stat_value(g, stat)} for g in games]
    all_values = [g["value"] for g in valued]

    last5 = all_values[:5]
    last10 = all_values[:10]
    home_values = [g["value"] for g in valued if g["is_home"]]
    away_values = [g["value"] for g in valued if not g["is_home"]]

    season_stats = _hit_rate(all_values, line, over)
    last10_stats = _hit_rate(last10, line, over)
    margin = round(season_stats["avg"] - line, 1)

    summary = {
        "season": season_stats,
        "last10": last10_stats,
        "last5": _hit_rate(last5, line, over),
        "home": _hit_rate(home_values, line, over),
        "away": _hit_rate(away_values, line, over),
    }

    # Optional opponent split.
    opp_split = None
    if opponent:
        opponent = opponent.upper()
        opp_values = [g["value"] for g in valued if g["opponent"] == opponent]
        opp_split = {"opponent": opponent, **_hit_rate(opp_values, line, over)}

    # Per-game log enriched with venue and hit/miss vs the line.
    game_log = []
    for g in valued:
        host = _host_team(g)
        v = venue(host)
        game_log.append({
            "date": g["date"],
            "matchup": g["matchup"],
            "opponent": g["opponent"],
            "is_home": g["is_home"],
            "arena": v["arena"],
            "city": v["city"],
            "min": g["MIN"],
            "value": g["value"],
            "hit": (g["value"] > line if over else g["value"] < line),
        })

    team_abbr = games[0]["team"] if games else ""

    return {
        "player": player_name,
        "player_id": player_id,
        "team": team_abbr,
        "stat": stat,
        "line": line,
        "over": over,
        "season": season,
        "lean": _lean(season_stats["rate"], last10_stats["rate"], margin),
        "margin": margin,
        "summary": summary,
        "opponent_split": opp_split,
        "median": median(all_values) if all_values else 0,
        "high": max(all_values) if all_values else 0,
        "low": min(all_values) if all_values else 0,
        "game_log": game_log,
    }


def analyze_prop(name: str, stat: str, line: float, over: bool = True,
                 season: str = DEFAULT_SEASON, opponent: str | None = None) -> dict:
    """Full prop analysis for a player/stat/line, fetching live NBA data."""
    player = find_player(name)
    games = get_full_game_log(player["id"], season)
    return analyze_from_games(
        player["full_name"], player["id"], games, stat, line, over, season, opponent
    )
