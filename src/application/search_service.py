import re
import json
import numpy as np
from typing import List, Optional
from src.domain.document import Document
from src.infrastructure.db import Database
from src.infrastructure.vector_index import VectorIndex
from src.application.llm_service import LLMService


class SearchResult:
    def __init__(self, doc_id: str, title: str, chunk_index: int, text: str,
                 score: float, page_start: Optional[int] = None, page_end: Optional[int] = None):
        self.doc_id = doc_id
        self.title = title
        self.chunk_index = chunk_index
        self.text = text
        self.score = score
        self.page_start = page_start
        self.page_end = page_end

    def to_dict(self):
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "score": round(self.score, 4),
            "page_start": self.page_start,
            "page_end": self.page_end,
        }


class SearchService:
    def __init__(self, db: Database, index: VectorIndex):
        self.db = db
        self.index = index

    async def index_document(self, doc: Document, llm: LLMService):
        texts = [c.text for c in doc.chunks]
        if not texts:
            return
        vectors = await llm.embed(texts)
        self.db.save_document(doc)
        # serialize vectors to bytes for storage
        byte_vectors = [v.tobytes() for v in vectors]
        indices = [c.index for c in doc.chunks]
        self.db.save_vectors(doc.id, indices, byte_vectors)
        # add to in-memory index
        for chunk, vec in zip(doc.chunks, vectors):
            self.index.add(doc.id, chunk.index, vec)

    async def semantic_search(self, query: str, llm: LLMService, top_k: int = 5) -> List[SearchResult]:
        q_vec = (await llm.embed([query]))[0]
        results = self.index.search(q_vec, top_k=top_k)
        out: List[SearchResult] = []
        for doc_id, chunk_idx, score in results:
            doc = self.db.get_document(doc_id)
            if not doc:
                continue
            chunk = next((c for c in doc.chunks if c.index == chunk_idx), None)
            if not chunk:
                continue
            out.append(SearchResult(
                doc_id=doc.id,
                title=doc.title,
                chunk_index=chunk.index,
                text=chunk.text,
                score=score,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            ))
        return out

    def keyword_search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT doc_id, chunk_index, text, page_start, page_end FROM chunks WHERE text LIKE ? LIMIT ?",
                (f"%{query}%", top_k * 10),
            ).fetchall()
        out: List[SearchResult] = []
        seen = set()
        for doc_id, chunk_idx, text, ps, pe in rows:
            if len(out) >= top_k:
                break
            key = (doc_id, chunk_idx)
            if key in seen:
                continue
            seen.add(key)
            doc = self.db.get_document(doc_id)
            title = doc.title if doc else doc_id
            # simple relevance score based on occurrences
            score = text.lower().count(query.lower()) / max(len(text.split()), 1)
            out.append(SearchResult(
                doc_id=doc_id, title=title, chunk_index=chunk_idx,
                text=text, score=score, page_start=ps, page_end=pe,
            ))
        return sorted(out, key=lambda x: x.score, reverse=True)

    async def match_legal_articles(self, query: str, llm: LLMService) -> dict:
        system_msg = (
            "你是一位台灣法律專家。請從使用者的問題中，找出最相關的法律名稱與條文編號，"
            "並簡要說明適用理由。請以 JSON 格式回應："
            '{"articles": [{"law": "法律名稱", "article": "條號", "reason": "適用理由"}]}'
        )
        content = await llm.chat([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query},
        ])
        # extract JSON if wrapped in markdown
        m = re.search(r"```json\s*(.*?)\s*```", content, re.S)
        if m:
            content = m.group(1)
        try:
            return json.loads(content)
        except Exception:
            return {"articles": [], "raw": content}

    def load_index_from_db(self):
        rows = self.db.get_all_vectors()
        dim = None
        for doc_id, chunk_idx, vec_bytes in rows:
            vec = np.frombuffer(vec_bytes, dtype=np.float32)
            if dim is None:
                dim = vec.shape[0]
            self.index.add(doc_id, chunk_idx, vec)
