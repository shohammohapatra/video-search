import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.embeddings.service import get_embedding_service
from app.ingestion.youtube import YoutubeDownloadError, download_youtube_video
from app.models.video import SourceType, Video, VideoChunk, VideoStatus
from app.rag.service import RAGService
from app.retrieval.service import RetrievalService
from app.schemas.search import AskRequest, AskResponse, SearchRequest, SearchResponse
from app.schemas.video import SegmentRead, VideoRead, VideoStatusRead, YoutubeIngestRequest
from app.utils.security import normalize_youtube_url, sanitize_filename, validate_upload
from app.workers.jobs import enqueue_video_processing

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/videos/upload", response_model=list[VideoRead], status_code=status.HTTP_201_CREATED)
def upload_videos(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    created: list[Video] = []
    for file in files:
        validate_upload(file)
        filename = sanitize_filename(file.filename or "video.mp4")
        video_id = uuid.uuid4()
        target = settings.storage_path / "videos" / f"{video_id}_{filename}"
        size = 0
        with target.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_size:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Video is too large")
                out.write(chunk)
        video = Video(
            id=video_id,
            title=Path(filename).stem,
            source_type=SourceType.upload,
            storage_path=str(target),
            status=VideoStatus.pending,
        )
        db.add(video)
        created.append(video)
    db.commit()
    for video in created:
        db.refresh(video)
        enqueue_video_processing(video.id)
    return created


@router.post("/videos/youtube", response_model=list[VideoRead], status_code=status.HTTP_201_CREATED)
def add_youtube_videos(payload: YoutubeIngestRequest, db: Session = Depends(get_db)):
    created: list[Video] = []
    for raw_url in payload.urls:
        try:
            url = normalize_youtube_url(str(raw_url))
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        video_id = uuid.uuid4()
        video = Video(
            id=video_id,
            title="Downloading YouTube video",
            source_type=SourceType.youtube,
            source_url=url,
            status=VideoStatus.downloading,
            progress=0.02,
        )
        db.add(video)
        db.commit()
        try:
            media_path, title = download_youtube_video(url, str(video_id), payload.resolution)
            video.title = title
            video.storage_path = str(media_path)
            video.status = VideoStatus.pending
            db.commit()
            enqueue_video_processing(video.id)
            created.append(video)
        except YoutubeDownloadError as exc:
            video.status = VideoStatus.failed
            video.processing_error = str(exc)
            db.commit()
            created.append(video)
    return created


@router.get("/videos", response_model=list[VideoRead])
def list_videos(db: Session = Depends(get_db)):
    return db.scalars(select(Video).order_by(Video.created_at.desc())).all()


@router.get("/videos/{video_id}", response_model=VideoRead)
def get_video(video_id: uuid.UUID, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return video


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: uuid.UUID, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    paths = [video.storage_path, video.thumbnail_path]
    db.delete(video)
    db.commit()
    for raw_path in paths:
        if raw_path:
            path = Path(raw_path)
            if path.exists() and settings.storage_path in path.parents:
                path.unlink(missing_ok=True)


@router.get("/videos/{video_id}/status", response_model=VideoStatusRead)
def video_status(video_id: uuid.UUID, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return VideoStatusRead(
        id=video.id,
        status=video.status,
        progress=video.progress,
        processing_error=video.processing_error,
    )


@router.get("/videos/{video_id}/segments", response_model=list[SegmentRead])
def video_segments(video_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.scalars(
        select(VideoChunk).where(VideoChunk.video_id == video_id).order_by(VideoChunk.start_time)
    ).all()


@router.get("/videos/{video_id}/stream")
def stream_video(video_id: uuid.UUID, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video or not video.storage_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    path = Path(video.storage_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video file not found")
    return FileResponse(path)


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    retriever = RetrievalService(db, get_embedding_service())
    results = retriever.search(payload.query, payload.video_ids, payload.top_k or settings.retrieval_top_k)
    return SearchResponse(results=[RetrievalService.source_payload(item) for item in results])


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    retriever = RetrievalService(db, get_embedding_service())
    retrieval_query = "\n".join([message.content for message in payload.history[-6:]] + [payload.question])
    evidence = retriever.search(retrieval_query, payload.video_ids, settings.retrieval_top_k)
    answer, grounded = RAGService().answer(payload.question, evidence, payload.history)
    sources = [RetrievalService.source_payload(item) for item in evidence[:5]] if grounded else []
    return AskResponse(answer=answer, grounded=grounded, sources=sources)
