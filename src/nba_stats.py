import unicodedata

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from tabulate import tabulate


def _normalize(text: str) -> str:
    """Lowercase and strip accents so 'Jokic' matches 'Jokić'."""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return no_accents.lower().strip()


def find_player(name: str) -> dict:
    """Return the best matching active player or raise if none found."""
    target = _normalize(name)
    all_players = players.get_active_players()

    # Exact full-name match first (accent-insensitive)
    for p in all_players:
        if _normalize(p["full_name"]) == target:
            return p

    # Partial match fallback
    matches = [p for p in all_players if target in _normalize(p["full_name"])]
    if not matches:
        raise ValueError(f"No active player found matching '{name}'.")
    if len(matches) > 1:
        names = ", ".join(p["full_name"] for p in matches[:5])
        raise ValueError(f"Multiple players matched '{name}': {names}. Be more specific.")
    return matches[0]


def fetch_game_log(player_id: int, season: str = "2024-25", last_n: int = 10) -> list[dict]:
    """Return the last N game log rows for a player."""
    log = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season,
        timeout=30,
    )
    df = log.get_data_frames()[0]

    if df.empty:
        raise ValueError("No game log data found for this player/season.")

    rows = []
    for _, row in df.head(last_n).iterrows():
        rows.append({
            "Date": row["GAME_DATE"],
            "Matchup": row["MATCHUP"],
            "MIN": row["MIN"],
            "PTS": int(row["PTS"]),
            "REB": int(row["REB"]),
            "AST": int(row["AST"]),
        })
    return rows


def compute_averages(game_log: list[dict]) -> dict:
    n = len(game_log)
    return {
        "MIN": round(sum(float(g["MIN"]) for g in game_log) / n, 1),
        "PTS": round(sum(g["PTS"] for g in game_log) / n, 1),
        "REB": round(sum(g["REB"] for g in game_log) / n, 1),
        "AST": round(sum(g["AST"] for g in game_log) / n, 1),
    }


def display(player_name: str, game_log: list[dict]) -> None:
    headers = ["Date", "Matchup", "MIN", "PTS", "REB", "AST"]
    rows = [[g[h] for h in headers] for g in game_log]

    print(f"\n{player_name} — Last {len(game_log)} Games\n")
    print(tabulate(rows, headers=headers, tablefmt="simple"))

    avgs = compute_averages(game_log)
    avg_row = [["", "AVERAGES", avgs["MIN"], avgs["PTS"], avgs["REB"], avgs["AST"]]]
    print(tabulate(avg_row, tablefmt="simple"))
    print()
