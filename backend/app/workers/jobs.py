import logging
from uuid import UUID

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingestion.video_processing import VideoProcessor
from app.workers.celery_app import process_video

logger = logging.getLogger(__name__)


def enqueue_video_processing(video_id: UUID) -> None:
    try:
        process_video.delay(str(video_id))
    except Exception:
        logger.warning("celery unavailable; processing video inline", exc_info=True)
        db = SessionLocal()
        try:
            VideoProcessor(db).process(video_id)
        finally:
            db.close()

