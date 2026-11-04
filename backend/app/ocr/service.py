from pathlib import Path
import subprocess
from typing import Protocol


class OCRService(Protocol):
    def extract_text(self, frame_path: Path) -> str:
        ...


class LocalOCRService(OCRService):
    def extract_text(self, frame_path: Path) -> str:
        sidecar = frame_path.with_suffix(".txt")
        if sidecar.exists():
            return sidecar.read_text().strip()
        try:
            result = subprocess.run(
                ["tesseract", str(frame_path), "stdout"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return ""


def get_ocr_service() -> OCRService:
    return LocalOCRService()
