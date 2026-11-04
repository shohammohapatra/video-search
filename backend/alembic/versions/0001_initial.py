"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    source_type = postgresql.ENUM("upload", "youtube", name="sourcetype")
    video_status = postgresql.ENUM("pending", "downloading", "processing", "ready", "failed", name="videostatus")
    source_type.create(op.get_bind(), checkfirst=True)
    video_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("storage_path", sa.Text()),
        sa.Column("thumbnail_path", sa.Text()),
        sa.Column("duration", sa.Float()),
        sa.Column("status", video_status, nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("processing_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_videos_status", "videos", ["status"])
    for table_name, time_cols in {
        "transcripts": [sa.Column("start_time", sa.Float(), nullable=False), sa.Column("end_time", sa.Float(), nullable=False)],
        "visual_segments": [sa.Column("timestamp", sa.Float(), nullable=False)],
        "video_chunks": [sa.Column("start_time", sa.Float(), nullable=False), sa.Column("end_time", sa.Float(), nullable=False)],
    }.items():
        columns = [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("video_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
            *time_cols,
        ]
        if table_name == "transcripts":
            columns += [sa.Column("text", sa.Text(), nullable=False), sa.Column("metadata", postgresql.JSONB())]
        elif table_name == "visual_segments":
            columns += [
                sa.Column("frame_path", sa.Text()),
                sa.Column("visual_description", sa.Text(), nullable=False),
                sa.Column("ocr_text", sa.Text(), nullable=False),
                sa.Column("metadata", postgresql.JSONB()),
            ]
        else:
            columns += [
                sa.Column("transcript", sa.Text(), nullable=False),
                sa.Column("visual_description", sa.Text(), nullable=False),
                sa.Column("ocr_text", sa.Text(), nullable=False),
                sa.Column("combined_text", sa.Text(), nullable=False),
                sa.Column("embedding", postgresql.JSONB()),
                sa.Column("metadata", postgresql.JSONB()),
            ]
        columns.append(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
        op.create_table(table_name, *columns)
        op.create_index(f"ix_{table_name}_video_id", table_name, ["video_id"])
    op.create_index("ix_video_chunks_video_time", "video_chunks", ["video_id", "start_time", "end_time"])


def downgrade() -> None:
    op.drop_index("ix_video_chunks_video_time", table_name="video_chunks")
    for table_name in ["video_chunks", "visual_segments", "transcripts"]:
        op.drop_table(table_name)
    op.drop_index("ix_videos_status", table_name="videos")
    op.drop_table("videos")
    postgresql.ENUM(name="videostatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="sourcetype").drop(op.get_bind(), checkfirst=True)

