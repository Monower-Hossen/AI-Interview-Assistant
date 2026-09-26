from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings
from rag.document_loader import Document


@dataclass
class TextChunk:
    text: str
    metadata: dict
    chunk_index: int
    source: str


class TextSplitter:
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.separators = separators or [
            "\n\n",
            "\n",
            ". ",
            ", ",
            " ",
        ]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def split_documents(self, documents: list[Document]) -> list[TextChunk]:
        all_chunks = []
        chunk_index = 0

        for doc in documents:
            chunks = self.splitter.split_text(doc.content)
            for chunk_text in chunks:
                if chunk_text.strip():
                    all_chunks.append(
                        TextChunk(
                            text=chunk_text.strip(),
                            metadata={**doc.metadata, "source": doc.source},
                            chunk_index=chunk_index,
                            source=doc.source,
                        )
                    )
                    chunk_index += 1

        return all_chunks

    def split_text(
        self, text: str, metadata: dict | None = None, source: str = ""
    ) -> list[TextChunk]:
        chunks = self.splitter.split_text(text)
        result = []
        for i, chunk_text in enumerate(chunks):
            if chunk_text.strip():
                result.append(
                    TextChunk(
                        text=chunk_text.strip(),
                        metadata=metadata or {},
                        chunk_index=i,
                        source=source,
                    )
                )
        return result


def create_text_splitter(
    chunk_size: int | None = None, chunk_overlap: int | None = None
) -> TextSplitter:
    return TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
