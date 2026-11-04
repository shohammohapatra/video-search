import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SourceType(str, enum.Enum):
    upload = "upload"
    youtube = "youtube"


class VideoStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    processing = "processing"
    ready = "ready"
    failed = "failed"


def json_type():
    from sqlalchemy import JSON

    return JSON().with_variant(JSONB, "postgresql")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    thumbnail_path: Mapped[str | None] = mapped_column(Text)
    duration: Mapped[float | None] = mapped_column(Float)
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus), default=VideoStatus.pending, index=True
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    processing_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["VideoChunk"]] = relationship(cascade="all, delete-orphan", back_populates="video")
    transcripts: Mapped[list["TranscriptSegment"]] = relationship(cascade="all, delete-orphan")
    visual_segments: Mapped[list["VisualSegment"]] = relationship(cascade="all, delete-orphan")


class TranscriptSegment(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VisualSegment(Base):
    __tablename__ = "visual_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    frame_path: Mapped[str | None] = mapped_column(Text)
    visual_description: Mapped[str] = mapped_column(Text, default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VideoChunk(Base):
    __tablename__ = "video_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, default="")
    visual_description: Mapped[str] = mapped_column(Text, default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    combined_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(json_type())
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped[Video] = relationship(back_populates="chunks")


Index("ix_video_chunks_video_time", VideoChunk.video_id, VideoChunk.start_time, VideoChunk.end_time)
