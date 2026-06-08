"""Tests for the Pro-gating predicate (pure — no network/DB)."""

from src.props import requires_pro, DEFAULT_SEASON


def test_basic_current_season_is_free():
    assert requires_pro(None, DEFAULT_SEASON) is False
    assert requires_pro("", DEFAULT_SEASON) is False


def test_opponent_split_requires_pro():
    assert requires_pro("BOS", DEFAULT_SEASON) is True


def test_past_season_requires_pro():
    assert requires_pro(None, "2023-24") is True


def test_opponent_and_past_season_requires_pro():
    assert requires_pro("LAL", "2022-23") is True
