"""Unit tests for the watchlist edge verdict (pure)."""

from src.watchlist import edge_verdict


def test_over_edge_flagged():
    v = edge_verdict(28.0, 25.5)
    assert v["side"] == "OVER" and v["edge"] == 2.5 and v["flagged"] is True


def test_under_edge_flagged():
    v = edge_verdict(20.0, 24.5)
    assert v["side"] == "UNDER" and v["flagged"] is True


def test_small_gap_not_flagged():
    v = edge_verdict(25.5, 25.0)
    assert v["side"] == "OVER" and v["flagged"] is False


def test_even_not_flagged():
    v = edge_verdict(25.0, 25.0)
    assert v["side"] == "EVEN" and v["flagged"] is False


def test_threshold_boundary_is_inclusive():
    assert edge_verdict(26.5, 25.0)["flagged"] is True  # exactly 1.5
