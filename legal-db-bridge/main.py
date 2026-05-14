"""MCP-to-HTTP Bridge for mcp-taiwan-legal-db."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from mcp_server.cache.db import CacheDB
from mcp_server.tools.regulations import RegulationClient, get_law_history
from mcp_server.tools.judicial_search import JudicialSearchClient
from mcp_server.tools.judicial_doc import JudgmentDocClient
from mcp_server.tools.waf_bypass import JudicialWAFBypass
from mcp_server.tools.constitutional_court import (
    get_interpretation as cc_get_interpretation,
    search_interpretations as cc_search_interpretations,
    get_citations as cc_get_citations,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("legal-db-bridge")

# Global clients
cache: Optional[CacheDB] = None
reg_client: Optional[RegulationClient] = None
jud_search: Optional[JudicialSearchClient] = None
jud_doc: Optional[JudgmentDocClient] = None
waf: Optional[JudicialWAFBypass] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cache, reg_client, jud_search, jud_doc, waf

    cache = CacheDB()
    await cache.initialize()
    await cache.cleanup_expired()
    await cache.cleanup_invalid_regulation_names()

    waf = JudicialWAFBypass()
    reg_client = RegulationClient(cache)
    jud_search = JudicialSearchClient(cache, waf)
    jud_doc = JudgmentDocClient(cache, waf)

    logger.info("Legal DB Bridge initialized")

    # Warmup WAF cookies in background
    asyncio.create_task(waf.ensure_ready())

    yield

    await reg_client.close()
    await jud_search.close()
    await jud_doc.close()
    await cache.close()
    logger.info("Legal DB Bridge shut down")


app = FastAPI(title="Taiwan Legal DB Bridge", lifespan=lifespan)


# ============================================================
# Request / Response models
# ============================================================

class SearchJudgmentsRequest(BaseModel):
    keyword: str = ""
    court: str = ""
    case_type: str = ""
    year_from: int = 0
    year_to: int = 0
    case_word: str = ""
    case_number: str = ""
    main_text: str = ""
    max_results: int = 10


class GetJudgmentRequest(BaseModel):
    jid: str = ""
    url: str = ""


class QueryRegulationRequest(BaseModel):
    law_name: str = ""
    pcode: str = ""
    article_no: str = ""
    from_no: str = ""
    to_no: str = ""
    include_history: bool = False


class GetPcodeRequest(BaseModel):
    law_name: str


class SearchRegulationsRequest(BaseModel):
    keyword: str
    offset: int = 0
    exclude_abolished: bool = False


class GetInterpretationRequest(BaseModel):
    case_id: str
    include_reasoning: bool = False
    reasoning_keyword: str = ""
    include_opinions: bool = False
    opinions_keyword: str = ""


class SearchInterpretationsRequest(BaseModel):
    keyword: str = ""
    year: int = 0
    number_from: int = 0
    number_to: int = 0


class GetCitationsRequest(BaseModel):
    case_id: str
    include_context: bool = False


# ============================================================
# Endpoints
# ============================================================

@app.post("/search_judgments")
async def search_judgments(req: SearchJudgmentsRequest):
    result = await jud_search.search(
        keyword=req.keyword,
        court=req.court,
        case_type=req.case_type,
        year_from=req.year_from,
        year_to=req.year_to,
        case_word=req.case_word,
        case_number=req.case_number,
        main_text=req.main_text,
        max_results=min(req.max_results, 200),
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@app.post("/get_judgment")
async def get_judgment(req: GetJudgmentRequest):
    if not req.jid and not req.url:
        raise HTTPException(status_code=400, detail="jid or url required")
    if req.jid:
        result = await jud_doc.get_by_jid(req.jid)
    else:
        result = await jud_doc.get_by_url(req.url)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@app.post("/query_regulation")
async def query_regulation(req: QueryRegulationRequest):
    # Resolve pcode
    pcode = req.pcode
    if not pcode and req.law_name:
        pcode = reg_client.resolve_pcode(req.law_name)
        if not pcode:
            raise HTTPException(
                status_code=404,
                detail=f"找不到法規「{req.law_name}」的代碼（pcode）。",
            )
    if not pcode:
        raise HTTPException(status_code=400, detail="須提供 law_name 或 pcode")

    if req.article_no:
        result = await reg_client.get_article(pcode, req.article_no)
    elif req.from_no and req.to_no:
        result = await reg_client.get_article_range(pcode, req.from_no, req.to_no)
    else:
        result = await reg_client.get_all_articles(pcode)

    if req.include_history and result.get("success"):
        history = get_law_history(pcode)
        if history:
            result["history"] = history

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@app.post("/get_pcode")
async def get_pcode(req: GetPcodeRequest):
    from mcp_server.tools.regulations import (
        _PCODE_ALL, _PCODE_REVERSE, _ABOLISHED_SET, reg_client as _rc
    )
    law_name = req.law_name
    if law_name in _PCODE_ALL:
        pcode = _PCODE_ALL[law_name]
        return {
            "success": True,
            "law_name": law_name,
            "pcode": pcode,
            "status": "已廢止" if pcode in _ABOLISHED_SET else "現行法規",
        }
    resolved = _rc.resolve_pcode(law_name)
    if resolved:
        full_name = _PCODE_REVERSE.get(resolved, law_name)
        return {
            "success": True,
            "law_name": full_name,
            "pcode": resolved,
            "matched_from": law_name,
            "status": "已廢止" if resolved in _ABOLISHED_SET else "現行法規",
        }
    suggestions = [name for name in _PCODE_ALL if law_name in name or name in law_name]
    return {
        "success": False,
        "error": f"找不到「{law_name}」對應的 pcode",
        "suggestions": suggestions[:10],
    }


@app.post("/search_regulations")
async def search_regulations(req: SearchRegulationsRequest):
    from mcp_server.tools.regulations import _PCODE_ALL, _ABOLISHED_SET
    if not req.keyword:
        raise HTTPException(status_code=400, detail="請提供搜尋關鍵字")
    matches = []
    for name, pcode in _PCODE_ALL.items():
        if req.keyword in name:
            if req.exclude_abolished and pcode in _ABOLISHED_SET:
                continue
            matches.append({
                "law_name": name,
                "pcode": pcode,
                "status": "已廢止" if pcode in _ABOLISHED_SET else "現行法規",
            })
    matches.sort(key=lambda m: (m["status"] != "現行法規", m["law_name"]))
    page_size = 50
    page = matches[req.offset:req.offset + page_size]
    return {
        "success": True,
        "keyword": req.keyword,
        "total_count": len(matches),
        "offset": req.offset,
        "has_more": req.offset + page_size < len(matches),
        "results": page,
    }


@app.post("/get_interpretation")
async def get_interpretation(req: GetInterpretationRequest):
    result = cc_get_interpretation(
        req.case_id,
        include_reasoning=req.include_reasoning,
        reasoning_keyword=req.reasoning_keyword,
        include_opinions=req.include_opinions,
        opinions_keyword=req.opinions_keyword,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@app.post("/search_interpretations")
async def search_interpretations(req: SearchInterpretationsRequest):
    result = cc_search_interpretations(
        keyword=req.keyword,
        year=req.year,
        number_from=req.number_from,
        number_to=req.number_to,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@app.post("/get_citations")
async def get_citations(req: GetCitationsRequest):
    result = cc_get_citations(req.case_id, include_context=req.include_context)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@app.get("/health")
async def health():
    return {"status": "ok"}
