"""
GraceFinance Legal Pages Router
=================================
Serves the compliance pages required for Stripe integration.
Add this to your existing FastAPI app — does not modify any existing routes.

Setup:
  1. Place the /static/legal/ folder in your project root
  2. Register this router in main.py (see bottom of file)
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter(tags=["legal"])

# Resolve the static directory relative to this file's location
# Adjust if your project structure differs
LEGAL_DIR = Path(__file__).parent / "static" / "legal"


def _serve_html(filename: str) -> HTMLResponse:
    """Read and return an HTML file from the legal directory."""
    filepath = LEGAL_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return HTMLResponse(content=filepath.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────
# Public legal page routes
# ─────────────────────────────────────────────

@router.get("/legal/terms", response_class=HTMLResponse)
def terms_of_service():
    """Terms of Service page."""
    return _serve_html("terms.html")


@router.get("/legal/privacy", response_class=HTMLResponse)
def privacy_policy():
    """Privacy Policy page."""
    return _serve_html("privacy.html")


@router.get("/legal/refund", response_class=HTMLResponse)
def refund_policy():
    """Refund and Dispute Policy page."""
    return _serve_html("refund.html")


# ─────────────────────────────────────────────
# Static CSS for legal pages
# ─────────────────────────────────────────────

@router.get("/static/legal/legal.css")
def legal_css():
    """Serve the shared legal pages stylesheet."""
    filepath = LEGAL_DIR / "legal.css"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Stylesheet not found")
    return FileResponse(filepath, media_type="text/css")


# ─────────────────────────────────────────────
# JSON endpoints (for frontend SPA consumption)
# ─────────────────────────────────────────────

@router.get("/api/legal/links")
def get_legal_links():
    """
    Return legal page URLs for use in footers, checkout flows, etc.
    Stripe Checkout can reference these in custom_text or metadata.
    """
    return {
        "terms_of_service": "/legal/terms",
        "privacy_policy": "/legal/privacy",
        "refund_policy": "/legal/refund",
    }


# ─────────────────────────────────────────────
# Integration instructions
# ─────────────────────────────────────────────
#
# In your main.py, add:
#
#   from legal_routes import router as legal_router
#   app.include_router(legal_router)
#
# That's it. No changes to existing routes.
#
# Your legal pages will be available at:
#   https://gracefinance.co/legal/terms
#   https://gracefinance.co/legal/privacy
#   https://gracefinance.co/legal/refund
#
# For Stripe Checkout, reference these URLs when creating sessions:
#
#   session = stripe.checkout.Session.create(
#       ...
#       consent_collection={"terms_of_service": "required"},
#       custom_text={
#           "terms_of_service_acceptance": {
#               "message": "I agree to the [Terms of Service](https://gracefinance.co/legal/terms) and [Privacy Policy](https://gracefinance.co/legal/privacy)"
#           }
#       },
#   )
#
# ─────────────────────────────────────────────