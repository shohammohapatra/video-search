from app.embeddings.service import HashingEmbeddingService
from app.rag.service import NOT_FOUND, RAGService
from app.retrieval.service import RetrievalService


def test_retrieval_finds_timestamped_segment(seeded_db):
    service = RetrievalService(seeded_db, HashingEmbeddingService())
    results = service.search("difference between clustered and non clustered indexes")
    assert results
    assert results[0].chunk.start_time == 497


def test_grounded_answer_supported(seeded_db):
    retrieval = RetrievalService(seeded_db, HashingEmbeddingService())
    evidence = retrieval.search("What is clustered indexing?")
    answer, grounded = RAGService().answer("What is clustered indexing?", evidence)
    assert grounded is True
    assert "Clustered indexes" in answer


def test_unsupported_question_rejected(seeded_db):
    retrieval = RetrievalService(seeded_db, HashingEmbeddingService())
    evidence = retrieval.search("time complexity of Dijkstra algorithm")
    answer, grounded = RAGService().answer("What is the time complexity of Dijkstra?", evidence)
    assert grounded is False
    assert answer == NOT_FOUND

