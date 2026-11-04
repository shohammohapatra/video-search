import logging
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.audio.service import SpeechToTextService, get_speech_service
from app.core.config import settings
from app.embeddings.service import EmbeddingService, get_embedding_service
from app.models.video import TranscriptSegment, Video, VideoChunk, VideoStatus, VisualSegment
from app.ocr.service import OCRService, get_ocr_service
from app.vision.service import VisionService, get_vision_service

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(
        self,
        db: Session,
        speech: SpeechToTextService | None = None,
        ocr: OCRService | None = None,
        vision: VisionService | None = None,
        embeddings: EmbeddingService | None = None,
    ) -> None:
        self.db = db
        self.speech = speech or get_speech_service()
        self.ocr = ocr or get_ocr_service()
        self.vision = vision or get_vision_service()
        self.embeddings = embeddings or get_embedding_service()

    def process(self, video_id: UUID | str) -> None:
        video_id = UUID(str(video_id))
        video = self.db.get(Video, video_id)
        if not video or not video.storage_path:
            return
        try:
            self._update(video, VideoStatus.processing, 0.05)
            path = Path(video.storage_path)
            video.duration = self._duration(path)
            audio_path = self._extract_audio(video.id, path)
            self._update(video, VideoStatus.processing, 0.25)
            transcripts = self._transcribe(video.id, audio_path)
            self._update(video, VideoStatus.processing, 0.45)
            visuals = self._extract_visuals(video, path, video.duration or 0)
            self._update(video, VideoStatus.processing, 0.7)
            self._chunk(video.id, transcripts, visuals, video.duration or 0)
            self._update(video, VideoStatus.ready, 1.0)
        except Exception as exc:
            logger.exception("video processing failed", extra={"video_id": str(video_id)})
            video.status = VideoStatus.failed
            video.processing_error = str(exc)
            self.db.commit()

    def _update(self, video: Video, status: VideoStatus, progress: float) -> None:
        video.status = status
        video.progress = progress
        self.db.commit()

    def _duration(self, path: Path) -> float:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _extract_audio(self, video_id: UUID, video_path: Path) -> Path:
        target = settings.storage_path / "audio" / f"{video_id}.wav"
        if shutil.which("ffmpeg"):
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(target)],
                check=True,
                capture_output=True,
            )
        return target

    def _transcribe(self, video_id: UUID, audio_path: Path) -> list[TranscriptSegment]:
        rows: list[TranscriptSegment] = []
        for segment in self.speech.transcribe(audio_path):
            row = TranscriptSegment(
                video_id=video_id,
                start_time=segment["start_time"],
                end_time=segment["end_time"],
                text=segment["text"],
            )
            self.db.add(row)
            rows.append(row)
        self.db.commit()
        return rows

    def _extract_visuals(self, video: Video, video_path: Path, duration: float) -> list[VisualSegment]:
        video_id = video.id
        rows: list[VisualSegment] = []
        frames_dir = settings.storage_path / "frames" / str(video_id)
        frames_dir.mkdir(parents=True, exist_ok=True)
        timestamps = self._sample_timestamps(duration)
        for index, timestamp in enumerate(timestamps, start=1):
            frame_path = frames_dir / f"{int(timestamp):06d}.jpg"
            if shutil.which("ffmpeg"):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        str(timestamp),
                        "-i",
                        str(video_path),
                        "-frames:v",
                        "1",
                        str(frame_path),
                    ],
                    capture_output=True,
                    check=False,
                )
            ocr_text = self.ocr.extract_text(frame_path) if frame_path.exists() else ""
            description = self.vision.describe_frame(frame_path, ocr_text)
            row = VisualSegment(
                video_id=video_id,
                timestamp=timestamp,
                frame_path=str(frame_path) if frame_path.exists() else None,
                visual_description=description,
                ocr_text=ocr_text,
            )
            self.db.add(row)
            rows.append(row)
            # Vision inference is the slowest stage; expose progress per frame.
            self._update(video, VideoStatus.processing, 0.45 + 0.25 * (index / len(timestamps)))
        self.db.commit()
        return rows

    def _sample_timestamps(self, duration: float) -> list[float]:
        if duration <= 0:
            return [0.0]
        step = max(3.0, settings.frame_sample_seconds)
        return [float(t) for t in range(0, int(duration) + 1, int(step))]

    def _chunk(
        self,
        video_id: UUID,
        transcripts: list[TranscriptSegment],
        visuals: list[VisualSegment],
        duration: float,
    ) -> None:
        if duration <= 0 and transcripts:
            duration = max(segment.end_time for segment in transcripts)
        duration = max(duration, settings.chunk_seconds)
        start = 0.0
        while start < duration:
            end = min(duration, start + settings.chunk_seconds)
            transcript = " ".join(
                seg.text for seg in transcripts if seg.start_time < end and seg.end_time >= start
            )
            visual_description = " ".join(
                seg.visual_description for seg in visuals if start <= seg.timestamp <= end
            )
            ocr_text = " ".join(seg.ocr_text for seg in visuals if start <= seg.timestamp <= end)
            combined = "\n".join(
                part
                for part in [
                    f"Transcript: {transcript}" if transcript else "",
                    f"Visual: {visual_description}" if visual_description else "",
                    f"OCR: {ocr_text}" if ocr_text else "",
                ]
                if part
            )
            if combined.strip():
                self.db.add(
                    VideoChunk(
                        video_id=video_id,
                        start_time=start,
                        end_time=end,
                        transcript=transcript,
                        visual_description=visual_description,
                        ocr_text=ocr_text,
                        combined_text=combined,
                        embedding=self.embeddings.embed(combined),
                    )
                )
            start = end
        self.db.commit()
