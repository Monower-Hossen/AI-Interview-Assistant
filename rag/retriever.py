import json
from dataclasses import dataclass
from typing import Any

from config.settings import settings
from rag.vector_store import create_vector_store


@dataclass
class RetrievalResult:
    text: str
    metadata: dict
    score: float
    source: str


class Retriever:
    def __init__(self, store_type: str | None = None, top_k: int | None = None):
        self.vector_store: Any = create_vector_store(store_type)
        self.top_k = top_k or settings.top_k_retrieval

    def add_documents(self, chunks) -> list[str]:
        return self.vector_store.add_documents(chunks)

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        top_k = top_k or self.top_k
        results = self.vector_store.search(query, top_k)

        return [
            RetrievalResult(
                text=doc.text,
                metadata=doc.metadata,
                score=score,
                source=doc.metadata.get("source", ""),
            )
            for doc, score in results
        ]

    def retrieve_by_vector(
        self, vector: list[float], top_k: int | None = None
    ) -> list[RetrievalResult]:
        top_k = top_k or self.top_k
        results = self.vector_store.search_by_vector(vector, top_k)

        return [
            RetrievalResult(
                text=doc.text,
                metadata=doc.metadata,
                score=score,
                source=doc.metadata.get("source", ""),
            )
            for doc, score in results
        ]

    def get_context(self, query: str, top_k: int | None = None, max_chars: int = 4000) -> str:
        results = self.retrieve(query, top_k)

        context_parts = []
        total_chars = 0

        for result in results:
            if total_chars + len(result.text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(result.text[:remaining] + "...")
                break

            context_parts.append(f"[Source: {result.source}]\n{result.text}")
            total_chars += len(result.text)

        return "\n\n---\n\n".join(context_parts)

    def clear(self):
        self.vector_store.clear()

    def count(self) -> int:
        return self.vector_store.count()


class MultiQueryRetriever:
    def __init__(self, retriever: Retriever, llm_service=None):
        self.retriever = retriever
        self.llm_service = llm_service

    def retrieve(
        self, query: str, top_k: int | None = None, generate_queries: bool = True
    ) -> list[RetrievalResult]:
        if not generate_queries or self.llm_service is None:
            return self.retriever.retrieve(query, top_k)

        sub_queries = self._generate_sub_queries(query)
        all_results = []
        seen_texts = set()

        for sub_query in [query] + sub_queries:
            results = self.retriever.retrieve(sub_query, top_k=top_k or 3)
            for result in results:
                if result.text not in seen_texts:
                    seen_texts.add(result.text)
                    all_results.append(result)

        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[: top_k or self.retriever.top_k]

    def _generate_sub_queries(self, query: str) -> list[str]:
        prompt = f"""Generate 3 alternative search queries for this question to improve retrieval.
        Original query: {query}
        
        Return only a JSON array of strings, e.g., ["query1", "query2", "query3"]"""

        try:
            response = self.llm_service.generate(prompt)
            queries = json.loads(response.content)
            if isinstance(queries, list):
                return queries[:3]
        except Exception:
            pass

        return []


def create_retriever(store_type: str | None = None, top_k: int | None = None) -> Retriever:
    return Retriever(store_type=store_type, top_k=top_k)
