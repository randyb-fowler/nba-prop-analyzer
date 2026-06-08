"""Unit tests for the slate parser. No network — feeds a synthetic
ScoreboardV3 'scoreboard' dict into the pure parse_board function.
"""

from src.slate import parse_board


def sample_board():
    return {
        "gameDate": "2025-01-15",
        "games": [
            {
                "gameId": "0022400561",
                "gameStatusText": "Final/OT ",
                "gameTimeUTC": "2025-01-16T00:00:00Z",
                "homeTeam": {"teamTricode": "PHI", "teamName": "76ers"},
                "awayTeam": {"teamTricode": "NYK", "teamName": "Knicks"},
            },
            {
                "gameId": "0022400562",
                "gameStatusText": "7:30 pm ET",
                "gameTimeUTC": "2025-01-16T00:30:00Z",
                "homeTeam": {"teamTricode": "BOS", "teamName": "Celtics"},
                "awayTeam": {"teamTricode": "LAL", "teamName": "Lakers"},
            },
        ],
    }


def test_parse_board_counts_games():
    out = parse_board(sample_board())
    assert out["date"] == "2025-01-15"
    assert len(out["games"]) == 2


def test_parse_board_maps_fields():
    g = parse_board(sample_board())["games"][0]
    assert g["away"] == "NYK" and g["home"] == "PHI"
    assert g["away_name"] == "Knicks" and g["home_name"] == "76ers"
    assert g["game_id"] == "0022400561"


def test_parse_board_strips_status_whitespace():
    g = parse_board(sample_board())["games"][0]
    assert g["status"] == "Final/OT"


def test_parse_board_empty_uses_fallback_date():
    out = parse_board({"games": []}, fallback_date="2026-06-07")
    assert out["date"] == "2026-06-07"
    assert out["games"] == []
