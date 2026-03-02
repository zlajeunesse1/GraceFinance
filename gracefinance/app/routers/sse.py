"""
SSE Router — Server-Sent Events for real-time index updates.

Endpoints:
  GET /events/index → SSE stream that emits when the index updates

Lightweight alternative to WebSockets. The frontend connects once
and receives events when new index data is published.

Falls back gracefully: if the client disconnects, they poll
GET /index/summary instead.

Place at: app/routers/sse.py
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.index_worker import get_cached_index

router = APIRouter(prefix="/events", tags=["Events"])
logger = logging.getLogger("gracefinance.sse")


@router.get("/index")
async def index_events(request: Request):
    """
    SSE stream for index updates.

    Emits:
      - `index_updated` when the cached index changes
      - `heartbeat` every 30 seconds to keep the connection alive

    The client should reconnect on disconnect with exponential backoff.
    """
    return StreamingResponse(
        _event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


async def _event_generator(request: Request):
    """
    Generator that yields SSE events.

    Strategy: Poll the in-memory cache every 10 seconds.
    If the cache timestamp changed → emit index_updated event.
    Every 30 seconds → emit heartbeat.

    This is deliberately simple. For production scale with
    many concurrent connections, swap to a pub/sub system
    (Redis pub/sub → broadcast to all SSE connections).
    """
    last_seen_ts = None
    heartbeat_counter = 0

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            cache = get_cached_index()
            current_ts = cache.get("last_updated_at")

            # Emit index_updated if the timestamp changed
            if current_ts and current_ts != last_seen_ts:
                last_seen_ts = current_ts
                data = json.dumps({
                    "gci": cache.get("gci"),
                    "csi": cache.get("csi"),
                    "dpi": cache.get("dpi"),
                    "frs": cache.get("frs"),
                    "trend": cache.get("trend_direction"),
                    "timestamp": current_ts,
                    "contributors": cache.get("contributors_today", 0),
                })
                yield f"event: index_updated\ndata: {data}\n\n"

            # Heartbeat every 30 seconds (3 cycles of 10s)
            heartbeat_counter += 1
            if heartbeat_counter >= 3:
                heartbeat_counter = 0
                ts = datetime.now(timezone.utc).isoformat()
                yield f"event: heartbeat\ndata: {{\"ts\": \"{ts}\"}}\n\n"

            await asyncio.sleep(10)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"SSE stream error: {e}")
