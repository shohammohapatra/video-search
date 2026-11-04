from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    video_ids: list[UUID] = []
    top_k: int | None = Field(default=None, ge=1, le=25)


class SourceRead(BaseModel):
    video_id: UUID
    video_title: str
    start_time: float
    end_time: float
    score: float
    excerpt: str
    youtube_url: str | None = None


class SearchResponse(BaseModel):
    results: list[SourceRead]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    video_ids: list[UUID] = []
    history: list["ChatMessage"] = Field(default_factory=list, max_length=20)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=3000)


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    sources: list[SourceRead]

