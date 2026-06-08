"""FastAPI backend for the NBA prop analyzer.

Serves a JSON API plus the static single-page frontend in web/.
Run with:  python -m uvicorn api.app:app --reload
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from nba_api.stats.static import players

from src.nba_stats import _normalize
from src.props import analyze_prop, supported_stats, supported_seasons, DEFAULT_SEASON, requires_pro
from src.injuries import get_team_injuries
from src.slate import get_slate, get_roster
from src.teams import TEAMS
from src.db import init_db
from src.auth import router as auth_router, get_current_user, user_payload, require_pro
from src.billing import router as billing_router

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="NBA Prop Analyzer", version="1.0")

# Signed-cookie sessions (used for OAuth state and the login session).
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "dev-insecure-secret-change-me"),
    same_site="lax",
    https_only=os.environ.get("APP_BASE_URL", "").startswith("https"),
)

app.include_router(auth_router)
app.include_router(billing_router)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/api/me")
def me(user=Depends(get_current_user)):
    """Current user + Pro status (or {authenticated: false})."""
    return user_payload(user)


@app.get("/api/stats")
def list_stats():
    """Stat keys the analyzer supports (for the dropdown)."""
    return {"stats": supported_stats()}


@app.get("/api/seasons")
def list_seasons():
    """Seasons offered in the UI, plus the default."""
    return {"seasons": supported_seasons(), "default": DEFAULT_SEASON}


@app.get("/api/players")
def search_players(q: str = Query("", min_length=0)):
    """Autocomplete: active players whose name contains the query."""
    q = _normalize(q)
    active = players.get_active_players()
    if not q:
        results = active[:20]
    else:
        results = [p for p in active if q in _normalize(p["full_name"])][:20]
    return {"players": [{"id": p["id"], "name": p["full_name"]} for p in results]}


@app.get("/api/teams")
def list_teams():
    """Team abbreviations + names (for the opponent dropdown)."""
    return {"teams": [{"abbr": a, "name": t["name"]} for a, t in TEAMS.items()]}


@app.get("/api/analyze")
def analyze(
    player: str = Query(..., min_length=1),
    stat: str = Query(...),
    line: float = Query(...),
    over: bool = Query(True),
    opponent: str | None = Query(None),
    season: str = Query(DEFAULT_SEASON),
    user=Depends(get_current_user),
):
    """Run a full prop analysis, optionally filtered to one opponent."""
    if requires_pro(opponent, season) and not (user and user.is_pro):
        raise HTTPException(
            status_code=402,
            detail="Opponent splits and past seasons are Pro features. Upgrade to unlock.",
        )
    try:
        return analyze_prop(player, stat, line, over, season=season, opponent=opponent)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # network / API errors from nba_api
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


@app.get("/api/compare")
def compare(
    player_a: str = Query(..., min_length=1),
    player_b: str = Query(..., min_length=1),
    stat: str = Query(...),
    line: float = Query(...),
    over: bool = Query(True),
    season: str = Query(DEFAULT_SEASON),
    user=Depends(require_pro),
):
    """Run the same prop analysis for two players, side by side (Pro only)."""
    try:
        return {
            "a": analyze_prop(player_a, stat, line, over, season=season),
            "b": analyze_prop(player_b, stat, line, over, season=season),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


@app.get("/api/injuries")
def injuries(team: str = Query(..., min_length=2)):
    """Current injury report for a team (best-effort via ESPN)."""
    try:
        return get_team_injuries(team.upper())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Injury source error: {e}")


@app.get("/api/slate")
def slate(date: str | None = Query(None, description="YYYY-MM-DD; defaults to today")):
    """The NBA games scheduled on a date (defaults to today)."""
    try:
        return get_slate(date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Slate source error: {e}")


@app.get("/api/roster")
def roster(team: str = Query(..., min_length=2)):
    """A team's roster (for picking a player off the slate)."""
    try:
        return get_roster(team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Roster source error: {e}")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


# Serve CSS/JS and any other static assets.
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
