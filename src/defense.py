"""Defense-adjusted matchups.

How tough is tonight's opponent against a given stat? Uses nba_api's
team "Opponent" stats (what each team allows per game) to rank the opponent
1-30, so the analyzer can flag a soft or tough matchup — the kind of edge
generalist stats apps don't surface.

`rank_for_team` is pure for unit testing; `get_matchup` fetches + delegates.
"""

from nba_api.stats.endpoints import leaguedashteamstats

from src.cache import ttl_cache
from src.props import DEFAULT_SEASON, STAT_DEFINITIONS
from src.teams import abbr_for_name, team_name

# Our stat -> the opponent columns whose sum it corresponds to.
DEF_STAT_MAP = {
    "PTS": ["OPP_PTS"],
    "REB": ["OPP_REB"],
    "AST": ["OPP_AST"],
    "STL": ["OPP_STL"],
    "BLK": ["OPP_BLK"],
    "3PM": ["OPP_FG3M"],
    "TOV": ["OPP_TOV"],
    "PRA": ["OPP_PTS", "OPP_REB", "OPP_AST"],
    "PR": ["OPP_PTS", "OPP_REB"],
    "PA": ["OPP_PTS", "OPP_AST"],
    "RA": ["OPP_REB", "OPP_AST"],
}


def rank_for_team(rows: list[dict], opp_abbr: str, columns: list[str]) -> dict | None:
    """Rank a team by how much of a stat it allows (1 = allows fewest = toughest).

    `rows` is a list of {"abbr", <OPP_ columns>}. Returns
    {allowed, rank, of, difficulty} or None if the team isn't found.
    """
    scored = []
    for r in rows:
        allowed = sum(r.get(c, 0) for c in columns)
        scored.append((r["abbr"], round(allowed, 1)))
    scored.sort(key=lambda x: x[1])  # ascending: least allowed first

    for i, (abbr, allowed) in enumerate(scored):
        if abbr == opp_abbr:
            rank = i + 1
            of = len(scored)
            # Proportional thirds so it works for any league size:
            # toughest third allows the fewest (good for UNDER), softest third
            # allows the most (good for OVER).
            if rank <= of / 3:
                difficulty = "Tough"
            elif rank > 2 * of / 3:
                difficulty = "Soft"
            else:
                difficulty = "Neutral"
            return {"allowed": allowed, "rank": rank, "of": of, "difficulty": difficulty}
    return None


@ttl_cache(21600)  # season-level data; refresh every 6h
def get_opponent_defense(season: str = DEFAULT_SEASON) -> list[dict]:
    """Per-team opponent stats (what each team allows per game)."""
    data = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense="Opponent",
        per_mode_detailed="PerGame",
        season=season,
        timeout=30,
    )
    df = data.get_data_frames()[0]
    rows = []
    for _, r in df.iterrows():
        abbr = abbr_for_name(r["TEAM_NAME"])
        if not abbr:
            continue
        rows.append({
            "abbr": abbr,
            "OPP_PTS": r["OPP_PTS"], "OPP_REB": r["OPP_REB"], "OPP_AST": r["OPP_AST"],
            "OPP_FG3M": r["OPP_FG3M"], "OPP_STL": r["OPP_STL"],
            "OPP_BLK": r["OPP_BLK"], "OPP_TOV": r["OPP_TOV"],
        })
    return rows


def get_matchup(opp_abbr: str, stat: str, season: str = DEFAULT_SEASON) -> dict | None:
    """Defense-adjusted matchup for an opponent + stat, or None."""
    stat = stat.upper()
    columns = DEF_STAT_MAP.get(stat)
    if not (opp_abbr and columns):
        return None
    try:
        rows = get_opponent_defense(season)
    except Exception:
        return None
    result = rank_for_team(rows, opp_abbr.upper(), columns)
    if not result:
        return None
    return {"opp": opp_abbr.upper(), "opp_name": team_name(opp_abbr.upper()), "stat": stat, **result}
