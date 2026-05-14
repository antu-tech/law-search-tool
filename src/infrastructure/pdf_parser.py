import fitz  # PyMuPDF
from typing import List
from src.domain.document import Chunk


def parse_pdf(file_path: str, chunk_size: int = 800, overlap: int = 100) -> List[Chunk]:
    doc = fitz.open(file_path)
    chunks: List[Chunk] = []
    current_text = ""
    current_start_page = 1
    chunk_index = 0

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        if not text.strip():
            continue

        current_text += text + "\n"

        while len(current_text) >= chunk_size:
            end = chunk_size
            # try to break at newline or period near boundary
            for i in range(chunk_size - 1, chunk_size - overlap, -1):
                if current_text[i] in "\n。；":
                    end = i + 1
                    break

            chunk_text = current_text[:end].strip()
            chunks.append(Chunk(
                text=chunk_text,
                index=chunk_index,
                page_start=current_start_page,
                page_end=page_num + 1,
            ))
            chunk_index += 1
            current_text = current_text[end - overlap:]
            current_start_page = page_num + 1

    if current_text.strip():
        chunks.append(Chunk(
            text=current_text.strip(),
            index=chunk_index,
            page_start=current_start_page,
            page_end=len(doc),
        ))

    doc.close()
    return chunks
