import os
import aiohttp
import numpy as np
from typing import List

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


class LLMService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = OPENAI_BASE_URL.rstrip("/")

    async def embed(self, texts: List[str]) -> List[np.ndarray]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "text-embedding-3-small",
            "input": texts,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Embedding failed: {resp.status} {text}")
                data = await resp.json()
                return [
                    np.array(item["embedding"], dtype=np.float32)
                    for item in data["data"]
                ]

    async def chat(self, messages: List[dict], model: str = "gpt-4o") -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Chat failed: {resp.status} {text}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
