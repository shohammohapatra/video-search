import math
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings.service import EmbeddingService
from app.models.video import Video, VideoChunk, VideoStatus
from app.utils.time import youtube_timestamp_url


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "does",
    "is",
    "of",
    "the",
    "to",
    "what",
    "when",
    "where",
    "why",
}


@dataclass
class RetrievalResult:
    chunk: VideoChunk
    video: Video
    score: float
    excerpt: str


def cosine(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (
        math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right)) or 1.0
    )


def keyword_score(query: str, text: str) -> float:
    query_terms = {term for term in TOKEN_RE.findall(query.lower()) if term not in STOPWORDS}
    if not query_terms:
        return 0.0
    text_terms = [term for term in TOKEN_RE.findall(text.lower()) if term not in STOPWORDS]
    text_set = set(text_terms)
    overlap = len(query_terms & text_set) / len(query_terms)
    phrase_bonus = 0.15 if query.lower() in text.lower() else 0.0
    return min(1.0, overlap + phrase_bonus)


def has_searchable_evidence(text: str) -> bool:
    lowered = text.lower()
    return bool(text.strip()) and "representative frame captured from video" not in lowered


def excerpt_for(query: str, text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    terms = TOKEN_RE.findall(query.lower())
    lower = compact.lower()
    hit = min([lower.find(term) for term in terms if lower.find(term) >= 0] or [0])
    start = max(0, hit - limit // 3)
    return compact[start : start + limit].strip() + "..."


class RetrievalService:
    def __init__(self, db: Session, embeddings: EmbeddingService) -> None:
        self.db = db
        self.embeddings = embeddings

    def search(self, query: str, video_ids: list[UUID] | None = None, top_k: int = 8) -> list[RetrievalResult]:
        query_embedding = self.embeddings.embed(query)
        stmt = select(VideoChunk, Video).join(Video, VideoChunk.video_id == Video.id).where(
            Video.status == VideoStatus.ready
        )
        if video_ids:
            stmt = stmt.where(Video.id.in_(video_ids))
        rows = self.db.execute(stmt).all()
        scored: list[RetrievalResult] = []
        for chunk, video in rows:
            if not has_searchable_evidence(chunk.combined_text):
                continue
            semantic = cosine(query_embedding, chunk.embedding)
            lexical = keyword_score(query, chunk.combined_text)
            score = 0.65 * semantic + 0.35 * lexical
            if lexical == 0 and not chunk.transcript and not chunk.ocr_text:
                continue
            if score > 0:
                scored.append(RetrievalResult(chunk, video, score, excerpt_for(query, chunk.combined_text)))
        scored.sort(key=lambda item: item.score, reverse=True)
        if not video_ids:
            return scored[:top_k]

        # Keep multi-video questions from being dominated by one video's top chunks.
        # Each selected video contributes its strongest result before remaining slots
        # are filled by the global ranking.
        by_video: dict[UUID, list[RetrievalResult]] = {}
        for item in scored:
            by_video.setdefault(item.video.id, []).append(item)
        diversified: list[RetrievalResult] = []
        for video_id in video_ids:
            candidates = by_video.get(video_id, [])
            if candidates:
                diversified.append(candidates[0])
        selected = {id(item.chunk) for item in diversified}
        diversified.extend(item for item in scored if id(item.chunk) not in selected)
        return diversified[:top_k]

    @staticmethod
    def source_payload(result: RetrievalResult) -> dict:
        return {
            "video_id": result.video.id,
            "video_title": result.video.title,
            "start_time": result.chunk.start_time,
            "end_time": result.chunk.end_time,
            "score": round(result.score, 4),
            "excerpt": result.excerpt,
            "youtube_url": youtube_timestamp_url(result.video.source_url, result.chunk.start_time)
            if result.video.source_type.value == "youtube"
            else None,
        }
