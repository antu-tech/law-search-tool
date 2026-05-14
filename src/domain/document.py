from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone
import hashlib


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None


@dataclass
class Document:
    id: str
    title: str
    content_type: str  # "pdf" | "docx"
    chunks: List[Chunk] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def generate_id(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]
