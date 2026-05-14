import numpy as np
from src.infrastructure.vector_index import VectorIndex


def test_add_and_search():
    idx = VectorIndex()
    vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec2 = np.array([0.2, 1.0, 0.0], dtype=np.float32)
    idx.add("doc1", 0, vec1)
    idx.add("doc2", 0, vec2)

    results = idx.search(vec1, top_k=2)
    assert len(results) == 2
    assert results[0][0] == "doc1"
    assert results[0][2] > 0.99


def test_remove_doc():
    idx = VectorIndex()
    idx.add("doc1", 0, np.array([1.0, 0.0], dtype=np.float32))
    idx.add("doc2", 0, np.array([0.2, 1.0], dtype=np.float32))
    idx.remove_doc("doc1")
    results = idx.search(np.array([1.0, 0.0], dtype=np.float32), top_k=2)
    assert len(results) == 1
    assert results[0][0] == "doc2"
