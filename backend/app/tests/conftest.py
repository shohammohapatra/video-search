import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.models.video import SourceType, Video, VideoChunk, VideoStatus
from app.embeddings.service import HashingEmbeddingService


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        engine = create_engine(f"sqlite:///{Path(tmp) / 'test.db'}", future=True)
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, future=True)
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()


@pytest.fixture()
def seeded_db(db: Session) -> Session:
    embeddings = HashingEmbeddingService()
    lecture = Video(
        title="DBMS Lecture 1",
        source_type=SourceType.upload,
        status=VideoStatus.ready,
        duration=800,
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)
    text = (
        "Transcript: Clustered indexes determine the physical ordering of table records. "
        "Non-clustered indexes store a separate structure that points back to the rows."
    )
    db.add(
        VideoChunk(
            video_id=lecture.id,
            start_time=497,
            end_time=530,
            transcript=text,
            visual_description="Slide comparing clustered index and non-clustered index.",
            ocr_text="CLUSTERED INDEX NON-CLUSTERED INDEX",
            combined_text=text,
            embedding=embeddings.embed(text),
        )
    )
    db.commit()
    return db

