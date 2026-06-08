"""Static reference data for the 30 NBA teams.

Keyed by the abbreviation nba_api uses in the MATCHUP field (e.g. "LAL").
Used for venue/location labels and for matching ESPN injury data by full name.
"""

TEAMS = {
    "ATL": {"name": "Atlanta Hawks",          "arena": "State Farm Arena",          "city": "Atlanta"},
    "BOS": {"name": "Boston Celtics",         "arena": "TD Garden",                 "city": "Boston"},
    "BKN": {"name": "Brooklyn Nets",          "arena": "Barclays Center",           "city": "Brooklyn"},
    "CHA": {"name": "Charlotte Hornets",      "arena": "Spectrum Center",           "city": "Charlotte"},
    "CHI": {"name": "Chicago Bulls",          "arena": "United Center",             "city": "Chicago"},
    "CLE": {"name": "Cleveland Cavaliers",    "arena": "Rocket Mortgage FieldHouse","city": "Cleveland"},
    "DAL": {"name": "Dallas Mavericks",       "arena": "American Airlines Center",  "city": "Dallas"},
    "DEN": {"name": "Denver Nuggets",         "arena": "Ball Arena",                "city": "Denver"},
    "DET": {"name": "Detroit Pistons",        "arena": "Little Caesars Arena",      "city": "Detroit"},
    "GSW": {"name": "Golden State Warriors",  "arena": "Chase Center",              "city": "San Francisco"},
    "HOU": {"name": "Houston Rockets",        "arena": "Toyota Center",             "city": "Houston"},
    "IND": {"name": "Indiana Pacers",         "arena": "Gainbridge Fieldhouse",     "city": "Indianapolis"},
    "LAC": {"name": "LA Clippers",            "arena": "Intuit Dome",               "city": "Inglewood"},
    "LAL": {"name": "Los Angeles Lakers",     "arena": "Crypto.com Arena",          "city": "Los Angeles"},
    "MEM": {"name": "Memphis Grizzlies",      "arena": "FedExForum",                "city": "Memphis"},
    "MIA": {"name": "Miami Heat",             "arena": "Kaseya Center",             "city": "Miami"},
    "MIL": {"name": "Milwaukee Bucks",        "arena": "Fiserv Forum",              "city": "Milwaukee"},
    "MIN": {"name": "Minnesota Timberwolves", "arena": "Target Center",             "city": "Minneapolis"},
    "NOP": {"name": "New Orleans Pelicans",   "arena": "Smoothie King Center",      "city": "New Orleans"},
    "NYK": {"name": "New York Knicks",        "arena": "Madison Square Garden",     "city": "New York"},
    "OKC": {"name": "Oklahoma City Thunder",  "arena": "Paycom Center",             "city": "Oklahoma City"},
    "ORL": {"name": "Orlando Magic",          "arena": "Kia Center",                "city": "Orlando"},
    "PHI": {"name": "Philadelphia 76ers",     "arena": "Wells Fargo Center",        "city": "Philadelphia"},
    "PHX": {"name": "Phoenix Suns",           "arena": "Footprint Center",          "city": "Phoenix"},
    "POR": {"name": "Portland Trail Blazers", "arena": "Moda Center",               "city": "Portland"},
    "SAC": {"name": "Sacramento Kings",       "arena": "Golden 1 Center",           "city": "Sacramento"},
    "SAS": {"name": "San Antonio Spurs",      "arena": "Frost Bank Center",         "city": "San Antonio"},
    "TOR": {"name": "Toronto Raptors",        "arena": "Scotiabank Arena",          "city": "Toronto"},
    "UTA": {"name": "Utah Jazz",              "arena": "Delta Center",              "city": "Salt Lake City"},
    "WAS": {"name": "Washington Wizards",     "arena": "Capital One Arena",         "city": "Washington"},
}


def team_name(abbr: str) -> str:
    return TEAMS.get(abbr, {}).get("name", abbr)


def abbr_for_name(full_name: str) -> str | None:
    """Reverse lookup: full team name -> abbreviation (case-insensitive)."""
    if not full_name:
        return None
    target = full_name.strip().lower()
    for abbr, t in TEAMS.items():
        if t["name"].lower() == target:
            return abbr
    return None


def venue(abbr: str) -> dict:
    """Return {'arena', 'city'} for the host team's abbreviation."""
    t = TEAMS.get(abbr)
    if not t:
        return {"arena": "Unknown", "city": abbr}
    return {"arena": t["arena"], "city": t["city"]}
