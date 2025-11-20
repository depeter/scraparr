"""WebSocket endpoints for real-time updates"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.progress_tracker import progress_tracker
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/execution/{execution_id}")
async def execution_progress(websocket: WebSocket, execution_id: int):
    """
    WebSocket endpoint for real-time execution progress updates

    Args:
        execution_id: Execution ID to monitor

    Returns:
        JSON messages with progress updates:
        {
            "execution_id": 123,
            "status": "running",
            "items_scraped": 150,
            "elapsed_seconds": 45.2,
            "message": "Processing grid point (45.5, 3.0)...",
            "timestamp": "2025-11-13T10:30:00"
        }
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for execution {execution_id}")

    try:
        # Subscribe to progress updates
        await progress_tracker.subscribe(execution_id, websocket)

        # Keep connection alive and listen for close
        while True:
            # Wait for client messages (or disconnect)
            try:
                data = await websocket.receive_text()
                # Echo back to confirm connection is alive
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error for execution {execution_id}: {e}")
    finally:
        # Unsubscribe on disconnect
        await progress_tracker.unsubscribe(execution_id, websocket)
        logger.info(f"WebSocket connection closed for execution {execution_id}")
