"""Progress tracking service for scraper executions"""
from typing import Dict, Set, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Progress update data"""
    execution_id: int
    status: str  # "running", "success", "failed"
    items_scraped: int
    elapsed_seconds: float
    message: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return asdict(self)


class ProgressTracker:
    """Track progress of running scrapers and broadcast updates"""

    def __init__(self):
        # execution_id -> list of websocket connections
        self._subscribers: Dict[int, Set] = {}
        # execution_id -> latest progress update
        self._progress: Dict[int, ProgressUpdate] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, execution_id: int, websocket) -> None:
        """Subscribe a websocket to execution updates"""
        async with self._lock:
            if execution_id not in self._subscribers:
                self._subscribers[execution_id] = set()
            self._subscribers[execution_id].add(websocket)
            logger.info(f"WebSocket subscribed to execution {execution_id}")

            # Send latest progress if available
            if execution_id in self._progress:
                try:
                    await websocket.send_json(self._progress[execution_id].to_dict())
                except Exception as e:
                    logger.error(f"Error sending initial progress: {e}")

    async def unsubscribe(self, execution_id: int, websocket) -> None:
        """Unsubscribe a websocket from execution updates"""
        async with self._lock:
            if execution_id in self._subscribers:
                self._subscribers[execution_id].discard(websocket)
                if not self._subscribers[execution_id]:
                    del self._subscribers[execution_id]
                logger.info(f"WebSocket unsubscribed from execution {execution_id}")

    async def update_progress(
        self,
        execution_id: int,
        status: str,
        items_scraped: int,
        elapsed_seconds: float,
        message: str
    ) -> None:
        """Update progress and broadcast to subscribers"""
        progress = ProgressUpdate(
            execution_id=execution_id,
            status=status,
            items_scraped=items_scraped,
            elapsed_seconds=elapsed_seconds,
            message=message
        )

        async with self._lock:
            self._progress[execution_id] = progress

            # Broadcast to all subscribers
            if execution_id in self._subscribers:
                dead_websockets = set()
                for websocket in self._subscribers[execution_id]:
                    try:
                        await websocket.send_json(progress.to_dict())
                    except Exception as e:
                        logger.error(f"Error sending progress update: {e}")
                        dead_websockets.add(websocket)

                # Remove dead connections
                for ws in dead_websockets:
                    self._subscribers[execution_id].discard(ws)

    async def complete_execution(self, execution_id: int) -> None:
        """Mark execution as complete and cleanup"""
        async with self._lock:
            # Clean up progress data
            if execution_id in self._progress:
                del self._progress[execution_id]

            # Close all websockets
            if execution_id in self._subscribers:
                del self._subscribers[execution_id]

    def get_latest_progress(self, execution_id: int) -> Optional[ProgressUpdate]:
        """Get latest progress for an execution"""
        return self._progress.get(execution_id)


# Global instance
progress_tracker = ProgressTracker()
