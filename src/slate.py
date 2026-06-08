"""Today's slate: the NBA games on a given date, plus team rosters.

Powers the homepage "what's on tonight" view. Clicking a player from the
slate deep-links into the analyzer with the opponent pre-filled.

Uses ScoreboardV3 (date-based, works year-round and historically) rather than
the live scoreboard, which only serves data during the season.
"""

from datetime import date

from nba_api.stats.endpoints import scoreboardv3, commonteamroster
from nba_api.stats.static import teams as static_teams

from src.cache import ttl_cache
from src.props import DEFAULT_SEASON


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


@ttl_cache(600)  # today's slate can change (scores/status); 10 min is safe
def get_slate(game_date: str | None = None) -> dict:
    """Return the games scheduled on a date (defaults to today).

    Shape: {"date": str, "games": [{game_id, status, time_utc,
    home, home_name, away, away_name}]}
    """
    game_date = game_date or _today()
    sb = scoreboardv3.ScoreboardV3(game_date=game_date, timeout=30)
    board = sb.get_dict().get("scoreboard", {})
    return parse_board(board, game_date)


def parse_board(board: dict, fallback_date: str = "") -> dict:
    """Pure transform of a ScoreboardV3 'scoreboard' dict into our shape."""
    games = []
    for g in board.get("games", []):
        home, away = g["homeTeam"], g["awayTeam"]
        games.append({
            "game_id": g.get("gameId"),
            "status": g.get("gameStatusText", "").strip(),
            "time_utc": g.get("gameTimeUTC", ""),
            "home": home.get("teamTricode"),
            "home_name": home.get("teamName"),
            "away": away.get("teamTricode"),
            "away_name": away.get("teamName"),
        })
    return {"date": board.get("gameDate", fallback_date), "games": games}


def _team_id(team_abbr: str):
    found = static_teams.find_team_by_abbreviation(team_abbr)
    return found["id"] if found else None


@ttl_cache(21600)  # rosters rarely change mid-season; 6h
def get_roster(team_abbr: str, season: str = DEFAULT_SEASON) -> dict:
    """Return a team's roster as {"team": abbr, "players": [{id, name}]}."""
    team_abbr = team_abbr.upper()
    team_id = _team_id(team_abbr)
    if team_id is None:
        raise ValueError(f"Unknown team abbreviation '{team_abbr}'.")

    roster = commonteamroster.CommonTeamRoster(
        team_id=team_id, season=season, timeout=30
    )
    df = roster.get_data_frames()[0]

    players = [
        {"id": int(row["PLAYER_ID"]), "name": row["PLAYER"]}
        for _, row in df.iterrows()
    ]
    return {"team": team_abbr, "players": players}
