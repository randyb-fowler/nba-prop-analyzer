"""Unit tests for the prop analysis engine. These hit no network --
they feed synthetic game logs into the pure analysis functions.
"""

from src.nba_stats import _normalize
from src.props import (
    analyze_from_games,
    stat_value,
    supported_stats,
    _hit_rate,
    _lean,
)


def make_game(team="LAL", opponent="BOS", is_home=True, pts=25, reb=8, ast=7,
              stl=1, blk=1, fg3m=2, tov=3, minutes=35, date="Jan 01, 2025"):
    loc = "vs." if is_home else "@"
    return {
        "date": date,
        "matchup": f"{team} {loc} {opponent}",
        "team": team,
        "is_home": is_home,
        "opponent": opponent,
        "MIN": minutes,
        "PTS": pts, "REB": reb, "AST": ast,
        "STL": stl, "BLK": blk, "FG3M": fg3m, "TOV": tov,
    }


# --- _normalize -----------------------------------------------------------

def test_normalize_strips_accents():
    assert _normalize("Nikola Jokić") == "nikola jokic"
    assert _normalize("Luka Dončić") == "luka doncic"

def test_normalize_lowercases_and_trims():
    assert _normalize("  LeBron James  ") == "lebron james"


# --- stat_value -----------------------------------------------------------

def test_stat_value_single():
    g = make_game(pts=30)
    assert stat_value(g, "PTS") == 30

def test_stat_value_combo_pra():
    g = make_game(pts=30, reb=10, ast=8)
    assert stat_value(g, "PRA") == 48

def test_stat_value_threes():
    g = make_game(fg3m=5)
    assert stat_value(g, "3PM") == 5

def test_all_supported_stats_are_computable():
    g = make_game()
    for s in supported_stats():
        assert isinstance(stat_value(g, s), int)


# --- _hit_rate ------------------------------------------------------------

def test_hit_rate_over():
    res = _hit_rate([10, 20, 30, 40], line=25, over=True)
    assert res == {"games": 4, "hits": 2, "rate": 50.0, "avg": 25.0}

def test_hit_rate_under():
    res = _hit_rate([10, 20, 30, 40], line=25, over=False)
    assert res["hits"] == 2

def test_hit_rate_empty():
    res = _hit_rate([], line=25, over=True)
    assert res == {"games": 0, "hits": 0, "rate": 0.0, "avg": 0.0}

def test_hit_rate_line_is_exclusive():
    # value exactly on the line is NOT a hit (push)
    assert _hit_rate([25], line=25, over=True)["hits"] == 0
    assert _hit_rate([25], line=25, over=False)["hits"] == 0


# --- _lean ----------------------------------------------------------------

def test_lean_over():
    assert _lean(season_rate=70, recent_rate=80, margin=5) == "OVER"

def test_lean_under():
    assert _lean(season_rate=30, recent_rate=20, margin=-5) == "UNDER"

def test_lean_pass_when_margin_disagrees():
    # high hit rate but average is below the line -> not a confident over
    assert _lean(season_rate=70, recent_rate=80, margin=-1) == "PASS"


# --- analyze_from_games ---------------------------------------------------

def test_analyze_full_shape():
    games = [make_game(pts=p) for p in (30, 28, 26, 24, 10)]
    res = analyze_from_games("Test Player", 1, games, "PTS", 25.0, over=True)
    assert res["player"] == "Test Player"
    assert res["stat"] == "PTS"
    assert res["team"] == "LAL"
    assert res["summary"]["season"]["games"] == 5
    assert res["summary"]["season"]["hits"] == 3  # 30,28,26 > 25
    assert res["high"] == 30 and res["low"] == 10
    assert len(res["game_log"]) == 5

def test_analyze_home_away_split():
    games = [
        make_game(pts=30, is_home=True),
        make_game(pts=10, is_home=True),
        make_game(pts=30, is_home=False),
    ]
    res = analyze_from_games("P", 1, games, "PTS", 25.0, over=True)
    assert res["summary"]["home"]["games"] == 2
    assert res["summary"]["away"]["games"] == 1
    assert res["summary"]["away"]["rate"] == 100.0

def test_analyze_opponent_split():
    games = [
        make_game(pts=30, opponent="BOS"),
        make_game(pts=12, opponent="BOS"),
        make_game(pts=40, opponent="MIA"),
    ]
    res = analyze_from_games("P", 1, games, "PTS", 25.0, over=True, opponent="BOS")
    assert res["opponent_split"]["opponent"] == "BOS"
    assert res["opponent_split"]["games"] == 2
    assert res["opponent_split"]["hits"] == 1

def test_analyze_game_log_has_venue():
    games = [make_game(team="LAL", opponent="BOS", is_home=True)]
    res = analyze_from_games("P", 1, games, "PTS", 25.0)
    g = res["game_log"][0]
    assert g["arena"] == "Crypto.com Arena"  # home -> Lakers' arena
    assert g["city"] == "Los Angeles"

def test_analyze_away_venue_is_opponent_arena():
    games = [make_game(team="LAL", opponent="BOS", is_home=False)]
    res = analyze_from_games("P", 1, games, "PTS", 25.0)
    assert res["game_log"][0]["arena"] == "TD Garden"  # away -> Celtics' arena

def test_analyze_rejects_bad_stat():
    try:
        analyze_from_games("P", 1, [make_game()], "XYZ", 10.0)
        assert False, "expected ValueError"
    except ValueError:
        pass
