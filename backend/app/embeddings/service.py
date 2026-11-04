import hashlib
import math
import re
from collections.abc import Iterable
from typing import Protocol

from app.core.config import settings


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


class EmbeddingService(Protocol):
    def embed(self, text: str) -> list[float]:
        ...

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class HashingEmbeddingService(EmbeddingService):
    def __init__(self, dimensions: int = settings.embedding_dimensions) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def get_embedding_service() -> EmbeddingService:
    return HashingEmbeddingService()
