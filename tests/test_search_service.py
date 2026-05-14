import pytest
import numpy as np
from unittest.mock import AsyncMock
from src.infrastructure.db import Database
from src.infrastructure.vector_index import VectorIndex
from src.application.search_service import SearchService
from src.domain.document import Document, Chunk
from src.application.kimi_service import KimiService


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def search_svc(temp_db):
    idx = VectorIndex()
    return SearchService(temp_db, idx)


@pytest.mark.asyncio
async def test_semantic_search(search_svc):
    mock_kimi = AsyncMock(spec=KimiService)
    mock_kimi.embed.return_value = [
        np.array([1.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0], dtype=np.float32),
    ]

    doc = Document(
        id="d1", title="test", content_type="pdf",
        chunks=[Chunk(text="hello", index=0), Chunk(text="world", index=1)],
    )
    await search_svc.index_document(doc, mock_kimi)
    mock_kimi.embed.return_value = [np.array([1.0, 0.0], dtype=np.float32)]
    results = await search_svc.semantic_search("hello", mock_kimi, top_k=2)
    assert len(results) >= 1
    assert results[0].doc_id == "d1"
