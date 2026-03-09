"""
Feed Router — Social Feed API Endpoints
v1.1 — SECURITY FIX: /generate-community-insight now requires admin auth
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/feed", tags=["feed"])

ADMIN_EMAILS = {"zaclajeunesse1@gmail.com"}


class FeedSettingsUpdate(BaseModel):
    sharing_enabled: Optional[bool] = None
    share_streaks: Optional[bool] = None
    share_tier_changes: Optional[bool] = None
    share_dimension_progress: Optional[bool] = None
    share_goals: Optional[bool] = None
    share_xp_milestones: Optional[bool] = None
    show_tier_on_profile: Optional[bool] = None
    show_scores_on_profile: Optional[bool] = None
    display_name: Optional[str] = None


class ReactionRequest(BaseModel):
    reaction_type: str


@router.get("/")
def get_feed_posts(limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0), tier: Optional[str] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.services.feed_service import get_feed as _get_feed
    posts = _get_feed(db, user_id=user.id, limit=limit, offset=offset, tier_filter=tier)
    return {"posts": posts, "count": len(posts)}


@router.post("/{post_id}/react")
def react_to_post(post_id: int, body: ReactionRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.services.feed_service import toggle_reaction
    valid = ["fire", "clap", "rocket", "heart", "strong"]
    if body.reaction_type not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid reaction. Use: {valid}")
    return toggle_reaction(db, post_id=post_id, user_id=user.id, reaction_type=body.reaction_type)


@router.get("/settings")
def get_feed_settings_endpoint(db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.services.feed_service import get_feed_settings
    s = get_feed_settings(db, user.id)
    return {"sharing_enabled": s.sharing_enabled, "share_streaks": s.share_streaks, "share_tier_changes": s.share_tier_changes, "share_dimension_progress": s.share_dimension_progress, "share_goals": s.share_goals, "share_xp_milestones": s.share_xp_milestones, "show_tier_on_profile": s.show_tier_on_profile, "show_scores_on_profile": s.show_scores_on_profile, "display_name": s.display_name}


@router.put("/settings")
def update_settings(body: FeedSettingsUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.services.feed_service import update_feed_settings
    updates = body.dict(exclude_none=True)
    settings = update_feed_settings(db, user.id, updates)
    return {"message": "Settings updated", "sharing_enabled": settings.sharing_enabled}


@router.post("/generate-community-insight")
def generate_insight(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """ADMIN ONLY — generate a community insight post."""
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required.")

    from app.services.feed_service import generate_community_insight
    post = generate_community_insight(db)
    if post:
        return {"message": "Community insight generated", "headline": post.headline}
    return {"message": "Not enough data to generate insight"}