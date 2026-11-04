from celery import Celery

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingestion.video_processing import VideoProcessor

celery_app = Celery("video_search", broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task(name="process_video")
def process_video(video_id: str) -> None:
    db = SessionLocal()
    try:
        VideoProcessor(db).process(video_id)
    finally:
        db.close()

