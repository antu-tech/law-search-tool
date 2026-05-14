import os
import aiohttp
from typing import Optional

LEGAL_DB_URL = os.getenv("LEGAL_DB_URL", "http://legal-db:8001")


class LegalDBClient:
    def __init__(self, base_url: str = LEGAL_DB_URL):
        self.base_url = base_url.rstrip("/")

    async def _post(self, path: str, payload: dict) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}{path}", json=payload
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"LegalDB error {resp.status}: {text}")
                return await resp.json()

    async def query_regulation(
        self,
        law_name: str = "",
        pcode: str = "",
        article_no: str = "",
        include_history: bool = False,
    ) -> dict:
        return await self._post("/query_regulation", {
            "law_name": law_name,
            "pcode": pcode,
            "article_no": article_no,
            "include_history": include_history,
        })

    async def search_regulations(self, keyword: str, exclude_abolished: bool = True) -> dict:
        return await self._post("/search_regulations", {
            "keyword": keyword,
            "exclude_abolished": exclude_abolished,
        })

    async def search_judgments(self, keyword: str, max_results: int = 5) -> dict:
        return await self._post("/search_judgments", {
            "keyword": keyword,
            "max_results": max_results,
        })

    async def get_interpretation(self, case_id: str) -> dict:
        return await self._post("/get_interpretation", {
            "case_id": case_id,
        })
