"""Unit tests for the defense-matchup logic (pure, no network)."""

from src.defense import DEF_STAT_MAP, rank_for_team
from src.props import supported_stats


def test_def_map_covers_every_supported_stat():
    for s in supported_stats():
        assert s in DEF_STAT_MAP, f"missing defense mapping for {s}"


def _rows(values):
    # values: {abbr: opp_pts}
    return [{"abbr": a, "OPP_PTS": v} for a, v in values.items()]


def test_rank_toughest_is_one():
    rows = _rows({"BOS": 105.0, "LAL": 112.0, "DEN": 118.0})
    out = rank_for_team(rows, "BOS", ["OPP_PTS"])
    assert out["rank"] == 1 and out["of"] == 3
    assert out["allowed"] == 105.0
    assert out["difficulty"] == "Tough"


def test_rank_softest_is_last():
    rows = _rows({"BOS": 105.0, "LAL": 112.0, "DEN": 118.0})
    out = rank_for_team(rows, "DEN", ["OPP_PTS"])
    assert out["rank"] == 3
    assert out["difficulty"] == "Soft"


def test_rank_combo_sums_columns():
    rows = [
        {"abbr": "BOS", "OPP_PTS": 100, "OPP_REB": 40, "OPP_AST": 20},  # 160
        {"abbr": "LAL", "OPP_PTS": 110, "OPP_REB": 45, "OPP_AST": 25},  # 180
    ]
    out = rank_for_team(rows, "LAL", ["OPP_PTS", "OPP_REB", "OPP_AST"])
    assert out["allowed"] == 180 and out["rank"] == 2


def test_rank_unknown_team_returns_none():
    rows = _rows({"BOS": 105.0})
    assert rank_for_team(rows, "MIA", ["OPP_PTS"]) is None
