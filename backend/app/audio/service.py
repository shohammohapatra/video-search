import json
import subprocess
from pathlib import Path
from typing import Protocol


class SpeechToTextService(Protocol):
    def transcribe(self, audio_path: Path) -> list[dict]:
        ...


class LocalSpeechToTextService(SpeechToTextService):
    """Uses whisper CLI when available, otherwise supports sidecar transcript JSON for tests/demos."""

    def transcribe(self, audio_path: Path) -> list[dict]:
        sidecar = audio_path.with_suffix(".transcript.json")
        if sidecar.exists():
            return json.loads(sidecar.read_text())
        try:
            result = subprocess.run(
                [
                    "whisper",
                    str(audio_path),
                    "--output_format",
                    "json",
                    "--output_dir",
                    str(audio_path.parent),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return []
        output_json = audio_path.with_suffix(".json")
        if not output_json.exists():
            _ = result
            return []
        payload = json.loads(output_json.read_text())
        return [
            {"start_time": float(seg["start"]), "end_time": float(seg["end"]), "text": seg["text"].strip()}
            for seg in payload.get("segments", [])
            if seg.get("text", "").strip()
        ]


def get_speech_service() -> SpeechToTextService:
    return LocalSpeechToTextService()
