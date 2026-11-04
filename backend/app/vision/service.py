import base64
import httpx
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class VisionService(Protocol):
    def describe_frame(self, frame_path: Path, ocr_text: str = "") -> str:
        ...


class LocalVisionService(VisionService):
    def describe_frame(self, frame_path: Path, ocr_text: str = "") -> str:
        if ocr_text:
            return f"Frame contains visible text: {ocr_text[:500]}"
        return f"Representative frame captured from video: {frame_path.name}"


class OpenAIVisionService(VisionService):
    def __init__(self) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.llm_api_key)

    def describe_frame(self, frame_path: Path, ocr_text: str = "") -> str:
        encoded = base64.b64encode(frame_path.read_bytes()).decode("ascii")
        response = self.client.responses.create(
            model=settings.vision_model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Describe only what is visibly present in this video frame. Identify objects, people, vehicles, signs, shops, screens, and relationships. Do not guess. Include visible OCR text if useful."},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}"},
                ],
            }],
        )
        return response.output_text.strip()


class OllamaVisionService(VisionService):
    def describe_frame(self, frame_path: Path, ocr_text: str = "") -> str:
        image = base64.b64encode(frame_path.read_bytes()).decode("ascii")
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": settings.vision_model,
                "prompt": "Describe only visible objects, vehicles, people, shops, signs and relationships. Do not guess. Return concise facts.",
                "images": [image],
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()


def get_vision_service() -> VisionService:
    if settings.vision_provider.lower() == "ollama":
        return OllamaVisionService()
    if settings.vision_provider.lower() == "openai" and settings.llm_api_key:
        return OpenAIVisionService()
    return LocalVisionService()
