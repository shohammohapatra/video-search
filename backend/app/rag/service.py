from typing import Protocol

import httpx

from app.retrieval.service import RetrievalResult
from app.schemas.search import ChatMessage
from app.core.config import settings


NOT_FOUND = "I couldn't find this information in the provided videos."
PLACEHOLDER_MARKERS = (
    "representative frame captured from video",
    "frame contains visible text:",
)


class LLMService(Protocol):
    def generate_answer(self, question: str, evidence: list[RetrievalResult], history: list[ChatMessage] | None = None) -> str:
        ...


class ExtractiveGroundedLLMService(LLMService):
    def generate_answer(self, question: str, evidence: list[RetrievalResult], history: list[ChatMessage] | None = None) -> str:
        if not evidence or evidence[0].score < 0.12:
            return NOT_FOUND
        best = evidence[:3]
        sentences: list[str] = []
        for item in best:
            for sentence in item.chunk.combined_text.replace("\n", " ").split("."):
                sentence = sentence.strip()
                if len(sentence) > 24 and not any(marker in sentence.lower() for marker in PLACEHOLDER_MARKERS):
                    sentences.append(sentence)
                    break
        if not sentences:
            return NOT_FOUND
        return " ".join(sentences)[:900].strip()


class OpenAILLMService(LLMService):
    def __init__(self) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.llm_api_key)

    def generate_answer(self, question: str, evidence: list[RetrievalResult], history: list[ChatMessage] | None = None) -> str:
        evidence = list({item.video.id: item for item in reversed(evidence[:5])}.values())
        context = "\n\n".join(
            f"[{item.video.title} {item.chunk.start_time:.1f}-{item.chunk.end_time:.1f}]\n{item.chunk.combined_text}"
            for item in evidence[:5]
        )
        response = self.client.responses.create(
            model=settings.model_name,
            instructions=(
                "You are a video-grounded question answering system. Answer only from the supplied video context. "
                "Do not use outside knowledge or invent visual details. If the context does not support the answer, "
                "reply exactly: I couldn't find this information in the provided videos. Keep the answer concise."
            ),
            input=f"Question: {question}\n\nVideo context:\n{context}",
        )
        return response.output_text.strip()


class OllamaLLMService(LLMService):
    def generate_answer(self, question: str, evidence: list[RetrievalResult], history: list[ChatMessage] | None = None) -> str:
        # Answer from one strongest chunk per actual video. Additional chunks remain
        # available as timestamped sources but must not be mistaken for new videos.
        evidence = list({item.video.id: item for item in reversed(evidence[:5])}.values())
        context = "\n\n".join(
            f"[SOURCE VIDEO: {item.video.title} | {item.chunk.start_time:.1f}-{item.chunk.end_time:.1f}]\n{item.chunk.combined_text}"
            for item in evidence[:5]
        )
        video_titles = list(dict.fromkeys(item.video.title for item in evidence[:5]))
        conversation = "\n".join(f"{message.role}: {message.content}" for message in (history or [])[-6:])
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": settings.model_name,
                "system": (
                    "You are answering from exactly these provided videos: "
                    f"{', '.join(video_titles)}. Answer only from the supplied video context. "
                    "A source chunk is not a separate video. Never invent video numbers or refer to chunks as new videos. "
                    "When comparing or describing videos, use their exact SOURCE VIDEO titles. "
                    "Do not use outside knowledge. If unsupported, reply exactly: "
                    "I couldn't find this information in the provided videos."
                ),
                "prompt": f"Conversation so far:\n{conversation}\n\nCurrent question: {question}\n\nVideo context:\n{context}",
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()


class GroundingVerifier:
    def verify(self, answer: str, evidence: list[RetrievalResult]) -> bool:
        if answer == NOT_FOUND:
            return False
        if any(marker in answer.lower() for marker in PLACEHOLDER_MARKERS):
            return False
        evidence_text = " ".join(item.chunk.combined_text.lower() for item in evidence[:5])
        answer_terms = {term for term in answer.lower().split() if len(term) > 4}
        if not answer_terms:
            return False
        overlap = sum(1 for term in answer_terms if term.strip(".,:;") in evidence_text)
        return overlap / max(1, len(answer_terms)) >= 0.45


class RAGService:
    def __init__(self, llm: LLMService | None = None, verifier: GroundingVerifier | None = None) -> None:
        self.llm = llm or (
            OllamaLLMService()
            if settings.llm_provider.lower() == "ollama"
            else OpenAILLMService()
            if settings.llm_provider.lower() == "openai" and settings.llm_api_key
            else ExtractiveGroundedLLMService()
        )
        self.verifier = verifier or GroundingVerifier()

    def answer(self, question: str, evidence: list[RetrievalResult], history: list[ChatMessage] | None = None) -> tuple[str, bool]:
        if not evidence or evidence[0].score < 0.12:
            return NOT_FOUND, False
        answer = self.llm.generate_answer(question, evidence, history)
        grounded = self.verifier.verify(answer, evidence)
        if not grounded:
            return NOT_FOUND, False
        return answer, True
