import sqlite3
import json
from typing import List, Optional, Tuple
from src.domain.document import Document, Chunk

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_path TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vectors (
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    vector BLOB NOT NULL,
    PRIMARY KEY (doc_id, chunk_index),
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
"""


class Database:
    def __init__(self, path: str = "data/law_search.db"):
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        import os
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def save_document(self, doc: Document):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?)",
                (doc.id, doc.title, doc.content_type, doc.created_at,
                 doc.source_path, json.dumps(doc.metadata)),
            )
            conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc.id,))
            for chunk in doc.chunks:
                conn.execute(
                    "INSERT INTO chunks (doc_id, chunk_index, text, page_start, page_end) VALUES (?,?,?,?,?)",
                    (doc.id, chunk.index, chunk.text, chunk.page_start, chunk.page_end),
                )

    def save_vectors(self, doc_id: str, chunk_indices: List[int], vectors: List[bytes]):
        with self._connect() as conn:
            conn.execute("DELETE FROM vectors WHERE doc_id = ?", (doc_id,))
            for idx, vec in zip(chunk_indices, vectors):
                conn.execute(
                    "INSERT INTO vectors (doc_id, chunk_index, vector) VALUES (?,?,?)",
                    (doc_id, idx, vec),
                )

    def get_document(self, doc_id: str) -> Optional[Document]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, content_type, created_at, source_path, metadata FROM documents WHERE id = ?",
                (doc_id,),
            ).fetchone()
            if not row:
                return None
            chunks = [
                Chunk(text=r[0], index=r[1], page_start=r[2], page_end=r[3])
                for r in conn.execute(
                    "SELECT text, chunk_index, page_start, page_end FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
                    (doc_id,),
                ).fetchall()
            ]
            return Document(
                id=row[0], title=row[1], content_type=row[2],
                created_at=row[3], source_path=row[4],
                metadata=json.loads(row[5]) if row[5] else {},
                chunks=chunks,
            )

    def list_documents(self) -> List[Tuple[str, str, str]]:
        with self._connect() as conn:
            return conn.execute("SELECT id, title, content_type FROM documents ORDER BY created_at DESC").fetchall()

    def delete_document(self, doc_id: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    def get_all_vectors(self) -> List[Tuple[str, int, bytes]]:
        with self._connect() as conn:
            return conn.execute("SELECT doc_id, chunk_index, vector FROM vectors").fetchall()
