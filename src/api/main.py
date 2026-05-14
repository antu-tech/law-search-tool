import os
import shutil
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from src.infrastructure.db import Database
from src.infrastructure.vector_index import VectorIndex
from src.application.parsing_service import ParsingService
from src.application.search_service import SearchService, SearchResult
from src.application.llm_service import LLMService
from src.infrastructure.legal_db_client import LegalDBClient

DB_PATH = os.getenv("SQLITE_PATH", "data/law_search.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

db = Database(DB_PATH)
index = VectorIndex()
parsing = ParsingService()
search = SearchService(db, index)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    search.load_index_from_db()
    yield


app = FastAPI(title="Law Search Tool", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/static"), name="static")


def _llm(api_key: Optional[str]) -> LLMService:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-Api-Key header")
    return LLMService(api_key)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("src/static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
):
    llm = _llm(x_api_key)
    safe_name = os.path.basename(file.filename or "untitled")
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="Only .pdf and .docx supported")

    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc = parsing.parse(file_path, safe_name)
        await search.index_document(doc, llm)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return {"id": doc.id, "title": doc.title, "chunks": len(doc.chunks)}


@app.get("/api/documents")
async def list_documents():
    rows = db.list_documents()
    return [{"id": r[0], "title": r[1], "type": r[2]} for r in rows]


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    db.delete_document(doc_id)
    index.remove_doc(doc_id)
    return {"deleted": doc_id}


@app.get("/api/search")
async def search_endpoint(
    q: str,
    mode: str = "semantic",  # semantic | keyword | hybrid
    top_k: int = 5,
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query required")

    results: List[SearchResult] = []

    if mode == "semantic":
        llm = _llm(x_api_key)
        results = await search.semantic_search(q, llm, top_k=top_k)
    elif mode == "keyword":
        results = search.keyword_search(q, top_k=top_k)
    elif mode == "hybrid":
        llm = _llm(x_api_key)
        sem = await search.semantic_search(q, llm, top_k=top_k)
        key = search.keyword_search(q, top_k=top_k)
        # merge and deduplicate
        seen = set()
        for r in sem + key:
            k = (r.doc_id, r.chunk_index)
            if k not in seen:
                seen.add(k)
                results.append(r)
        results = sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
    else:
        raise HTTPException(status_code=400, detail="mode must be semantic, keyword, or hybrid")

    return {"query": q, "mode": mode, "results": [r.to_dict() for r in results]}


@app.get("/api/legal-articles")
async def legal_articles(
    q: str,
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
):
    llm = _llm(x_api_key)
    legal_db = LegalDBClient()
    return await search.match_legal_articles(q, llm, legal_db)


# ============================================================
# Direct MCP tool endpoints (no LLM key required)
# ============================================================

@app.post("/api/legal/query-regulation")
async def api_query_regulation(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db.query_regulation(
            law_name=payload.get("law_name", ""),
            pcode=payload.get("pcode", ""),
            article_no=payload.get("article_no", ""),
            include_history=payload.get("include_history", False),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/legal/search-regulations")
async def api_search_regulations(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db.search_regulations(
            keyword=payload.get("keyword", ""),
            exclude_abolished=payload.get("exclude_abolished", True),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/legal/get-pcode")
async def api_get_pcode(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db._post("/get_pcode", {"law_name": payload.get("law_name", "")})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/legal/search-judgments")
async def api_search_judgments(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db.search_judgments(
            keyword=payload.get("keyword", ""),
            max_results=payload.get("max_results", 10),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/legal/get-judgment")
async def api_get_judgment(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db._post("/get_judgment", payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/legal/get-interpretation")
async def api_get_interpretation(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db.get_interpretation(payload.get("case_id", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/legal/search-interpretations")
async def api_search_interpretations(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db._post("/search_interpretations", payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/legal/get-citations")
async def api_get_citations(payload: dict):
    legal_db = LegalDBClient()
    try:
        return await legal_db._post("/get_citations", payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
