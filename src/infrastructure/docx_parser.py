from typing import List
from docx import Document as DocxDocument
from src.domain.document import Chunk


def parse_docx(file_path: str, chunk_size: int = 800, overlap: int = 100) -> List[Chunk]:
    doc = DocxDocument(file_path)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    chunks: List[Chunk] = []
    idx = 0
    start = 0
    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        # soft break
        if end < len(full_text):
            for i in range(end, max(start, end - overlap), -1):
                if full_text[i] in "\n。；":
                    end = i + 1
                    break
        chunk_text = full_text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(text=chunk_text, index=idx))
            idx += 1
        start = end - overlap if end < len(full_text) else end

    return chunks
