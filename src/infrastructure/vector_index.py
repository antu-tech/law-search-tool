import numpy as np
from typing import List, Tuple


class VectorIndex:
    """Lightweight in-memory vector index using NumPy."""

    def __init__(self):
        self._vectors: np.ndarray = np.zeros((0, 1), dtype=np.float32)
        self._ids: List[Tuple[str, int]] = []  # (doc_id, chunk_index)

    def add(self, doc_id: str, chunk_index: int, vector: np.ndarray):
        if self._vectors.shape[0] == 0:
            self._vectors = vector.reshape(1, -1)
        else:
            self._vectors = np.vstack([self._vectors, vector.reshape(1, -1)])
        self._ids.append((doc_id, chunk_index))

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, int, float]]:
        if self._vectors.shape[0] == 0:
            return []
        q = query_vector.reshape(1, -1)
        # cosine similarity
        norms = np.linalg.norm(self._vectors, axis=1) * np.linalg.norm(q)
        norms[norms == 0] = 1e-10
        sims = np.dot(self._vectors, q.T).flatten() / norms
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [
            (self._ids[i][0], self._ids[i][1], float(sims[i]))
            for i in top_idx if sims[i] > 1e-6
        ]

    def remove_doc(self, doc_id: str):
        keep = [i for i, (d, _) in enumerate(self._ids) if d != doc_id]
        self._vectors = self._vectors[keep] if keep else np.zeros((0, self._vectors.shape[1]), dtype=np.float32)
        self._ids = [self._ids[i] for i in keep]

    def clear(self):
        self._vectors = np.zeros((0, 1), dtype=np.float32)
        self._ids = []
