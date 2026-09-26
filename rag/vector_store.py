from dataclasses import dataclass
from typing import Any

import numpy as np

from config.settings import settings
from rag.text_splitter import TextChunk


@dataclass
class VectorDocument:
    text: str
    metadata: dict
    score: float = 0.0
    id: int = 0


class FAISSVectorStore:
    def __init__(
        self,
        embedding_model: Any | None = None,
        dimension: int | None = None,
    ):
        from rag.embeddings import get_embedding_model

        self.embedding_model = embedding_model or get_embedding_model()
        self.dimension = dimension or self.embedding_model.dimension
        self.index: Any = None
        try:
            import faiss

            self.index = faiss.IndexFlatIP(self.dimension)
        except ImportError:
            self._faiss_available = False
        else:
            self._faiss_available = True
        self.documents: list[VectorDocument] = []
        self._fallback_embeddings: list[np.ndarray] = []

    def add_documents(self, chunks: list[TextChunk]) -> list[str]:
        if not chunks:
            return []
        texts = [c.text for c in chunks]
        embeddings = self.embedding_model.encode(texts)
        embedding_array = np.array(embeddings).astype("float32")

        if self._faiss_available:
            self.index.add(embedding_array)
        else:
            if not hasattr(self, "_fallback_embeddings"):
                self._fallback_embeddings = []
            self._fallback_embeddings.extend(embedding_array)

        ids = []
        for i, chunk in enumerate(chunks):
            doc = VectorDocument(
                text=chunk.text,
                metadata=chunk.metadata,
                id=len(self.documents),
            )
            self.documents.append(doc)
            ids.append(str(doc.id))
        return ids

    def search(self, query: str, top_k: int | None = None) -> list[tuple[VectorDocument, float]]:
        top_k = top_k or settings.top_k_retrieval
        query_embedding = self.embedding_model.encode([query])
        return self._search_by_embeddings(np.array(query_embedding).astype("float32"), top_k)

    def search_by_vector(
        self, vector: list[float], top_k: int | None = None
    ) -> list[tuple[VectorDocument, float]]:
        top_k = top_k or settings.top_k_retrieval
        query_vec = np.array(vector).reshape(1, -1).astype("float32")
        return self._search_by_embeddings(query_vec, top_k)

    def _search_by_embeddings(
        self, query_embedding: np.ndarray, top_k: int
    ) -> list[tuple[VectorDocument, float]]:
        if self._faiss_available and self.index is not None:
            scores, indices = self.index.search(query_embedding, top_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    doc.score = float(score)
                    results.append((doc, float(score)))
            return results

        if not hasattr(self, "_fallback_embeddings") or not self._fallback_embeddings:
            return []

        all_embeddings = np.vstack(self._fallback_embeddings)
        query_vec = query_embedding.reshape(1, -1)
        similarities = (all_embeddings @ query_vec.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if idx < len(self.documents):
                doc = self.documents[idx]
                doc.score = float(similarities[idx])
                results.append((doc, float(similarities[idx])))
        return results

    def clear(self) -> None:
        if self._faiss_available and self.index is not None:
            self.index = type(self.index)(self.dimension)
        if hasattr(self, "_fallback_embeddings"):
            self._fallback_embeddings = []
        self.documents = []

    def count(self) -> int:
        if self._faiss_available and self.index is not None:
            return int(self.index.ntotal)
        if hasattr(self, "_fallback_embeddings"):
            return len(self._fallback_embeddings)
        return len(self.documents)


def create_vector_store(store_type: str | None = None, **kwargs: Any) -> FAISSVectorStore:
    if store_type and store_type.lower() != "faiss":
        raise ValueError(f"Unsupported vector store type: {store_type}. Only 'faiss' is supported.")
    return FAISSVectorStore(**kwargs)
