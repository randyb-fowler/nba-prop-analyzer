"""Unit tests for the odds module's pure helpers (no network)."""

from src.odds import MARKET_MAP, match_event, parse_event_odds
from src.props import supported_stats


def test_market_map_covers_every_supported_stat():
    for s in supported_stats():
        assert s in MARKET_MAP, f"missing odds market mapping for {s}"


def test_match_event_by_home_or_away():
    events = [
        {"id": "1", "home_team": "New York Knicks", "away_team": "San Antonio Spurs"},
        {"id": "2", "home_team": "Boston Celtics", "away_team": "Miami Heat"},
    ]
    assert match_event(events, "San Antonio Spurs")["id"] == "1"
    assert match_event(events, "Boston Celtics")["id"] == "2"
    assert match_event(events, "Los Angeles Lakers") is None


SAMPLE_EVENT_ODDS = {
    "bookmakers": [
        {
            "key": "draftkings",
            "title": "DraftKings",
            "markets": [
                {
                    "key": "player_points",
                    "outcomes": [
                        {"name": "Over", "description": "Nikola Jokić", "price": -115, "point": 28.5},
                        {"name": "Under", "description": "Nikola Jokić", "price": -105, "point": 28.5},
                        {"name": "Over", "description": "Jamal Murray", "price": -110, "point": 21.5},
                    ],
                }
            ],
        }
    ]
}


def test_parse_event_odds_extracts_line_and_prices():
    out = parse_event_odds(SAMPLE_EVENT_ODDS, "Nikola Jokic", "player_points")
    assert out == {
        "book": "DraftKings",
        "line": 28.5,
        "over_price": -115,
        "under_price": -105,
    }


def test_parse_event_odds_accent_insensitive():
    # query without accent still matches "Nikola Jokić"
    assert parse_event_odds(SAMPLE_EVENT_ODDS, "nikola jokic", "player_points")["line"] == 28.5


def test_parse_event_odds_player_not_found():
    assert parse_event_odds(SAMPLE_EVENT_ODDS, "LeBron James", "player_points") is None


def test_parse_event_odds_wrong_market():
    assert parse_event_odds(SAMPLE_EVENT_ODDS, "Nikola Jokic", "player_rebounds") is None
