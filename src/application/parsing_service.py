import os
from typing import List
from src.domain.document import Document, Chunk
from src.infrastructure.pdf_parser import parse_pdf
from src.infrastructure.docx_parser import parse_docx


class ParsingService:
    def parse(self, file_path: str, original_name: str) -> Document:
        ext = os.path.splitext(original_name)[1].lower()
        content_type = "pdf" if ext == ".pdf" else "docx"

        if content_type == "pdf":
            chunks = parse_pdf(file_path)
        else:
            chunks = parse_docx(file_path)

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        return Document(
            id=Document.generate_id(file_bytes),
            title=original_name,
            content_type=content_type,
            chunks=chunks,
            source_path=file_path,
        )
