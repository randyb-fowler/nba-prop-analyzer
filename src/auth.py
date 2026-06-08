"""Google OAuth sign-in and session/user helpers.

The login session is just `request.session["user_id"]` backed by Starlette's
signed-cookie SessionMiddleware (added in api/app.py). If Google credentials
aren't configured the app still boots — only the login route reports 503 — so
the rest of the product keeps working.
"""

import os

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from src.db import User, get_db

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
GOOGLE_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

oauth = OAuth()
if GOOGLE_CONFIGURED:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Dependencies ---------------------------------------------------------

def get_current_user(request: Request, db=Depends(get_db)) -> User | None:
    """Return the logged-in User, or None if anonymous."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_pro(user: User | None = Depends(get_current_user)) -> User:
    """Gate a route to Pro subscribers. 401 if anonymous, 402 if not Pro."""
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to use this feature.")
    if not user.is_pro:
        raise HTTPException(status_code=402, detail="Upgrade to Pro to use this feature.")
    return user


def _upsert_user(db, sub: str, email: str, name: str) -> User:
    user = db.scalar(select(User).where(User.google_sub == sub))
    if user is None:
        user = User(google_sub=sub, email=email, name=name)
        db.add(user)
    else:
        user.email = email or user.email
        user.name = name or user.name
    db.commit()
    db.refresh(user)
    return user


# --- Routes ---------------------------------------------------------------

@router.get("/login")
async def login(request: Request):
    if not GOOGLE_CONFIGURED:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    redirect_uri = f"{APP_BASE_URL}/api/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def callback(request: Request, db=Depends(get_db)):
    if not GOOGLE_CONFIGURED:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {e}")

    info = token.get("userinfo") or {}
    sub = info.get("sub")
    if not sub:
        raise HTTPException(status_code=400, detail="Could not read Google profile.")

    user = _upsert_user(db, sub, info.get("email", ""), info.get("name", ""))
    request.session["user_id"] = user.id
    return RedirectResponse(url="/")


@router.post("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    return {"ok": True}


def user_payload(user: User | None) -> dict:
    """Serialize the current user for /api/me (shared with the frontend)."""
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "email": user.email,
        "name": user.name,
        "is_pro": user.is_pro,
    }
