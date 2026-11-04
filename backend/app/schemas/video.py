from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.models.video import SourceType, VideoStatus


class VideoRead(BaseModel):
    id: UUID
    title: str
    source_type: SourceType
    source_url: str | None
    thumbnail_path: str | None
    duration: float | None
    status: VideoStatus
    progress: float
    processing_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class YoutubeIngestRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=20)
    resolution: Literal[360, 480, 720, 1080] = 720


class VideoStatusRead(BaseModel):
    id: UUID
    status: VideoStatus
    progress: float
    processing_error: str | None


class SegmentRead(BaseModel):
    id: UUID
    video_id: UUID
    start_time: float
    end_time: float
    transcript: str
    visual_description: str
    ocr_text: str
    combined_text: str

    model_config = {"from_attributes": True}

