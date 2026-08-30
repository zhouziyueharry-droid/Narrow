from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from shopping_agent.domain.product_text import _text
from shopping_agent.retrieval.lexical import CatalogIndex


DocumentView = Literal["identity", "semantic", "combined"]


class SentenceTransformerDenseIndex:
    """Exact in-memory dense retrieval with a persistent embedding cache.

    The optional FAISS backend is preferred when installed. A NumPy exact-dot
    fallback keeps the implementation portable and has identical recall for the
    50k-product competition catalog.
    """

    CACHE_VERSION = 1

    def __init__(
        self,
        catalog: CatalogIndex,
        *,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: str | Path = ".cache/coarse_retrieval",
        document_view: DocumentView = "combined",
        batch_size: int = 128,
        max_seq_length: int = 192,
        use_faiss: bool = False,
        device: str | None = None,
    ) -> None:
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised by optional install
            raise RuntimeError(
                "Install the retrieval extra: uv sync --extra retrieval"
            ) from exc

        self._np = np
        self.catalog = catalog
        self.model_name = model_name
        self.document_view = document_view
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.use_faiss = use_faiss
        self._sentence_transformer_cls = SentenceTransformer
        self._device = device
        self.model = None
        self.asins = list(catalog.products)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = self._cache_key()
        self.embedding_path = self.cache_dir / f"{cache_key}.npy"
        self.metadata_path = self.cache_dir / f"{cache_key}.json"
        self.embeddings = self._load_or_encode()
        self.embedding_shape = tuple(self.embeddings.shape)
        self._faiss_index = self._build_faiss_index()
        if self._faiss_index is not None:
            # IndexFlatIP owns an exact in-memory copy. Keeping the mmap pages
            # referenced as well creates an avoidable peak when PyTorch encodes
            # the first online query on memory-constrained laptops.
            self.embeddings = None
            gc.collect()
        self._ensure_model()

    def _ensure_model(self):
        if self.model is None:
            self.model = self._sentence_transformer_cls(self.model_name, device=self._device)
            self.model.max_seq_length = self.max_seq_length
        return self.model

    def _cache_key(self) -> str:
        catalog_stat = self.catalog.catalog_path.stat()
        payload = json.dumps({
            "version": self.CACHE_VERSION,
            "catalog_size": catalog_stat.st_size,
            "catalog_mtime_ns": catalog_stat.st_mtime_ns,
            "model": self.model_name,
            "view": self.document_view,
            "max_seq_length": self.max_seq_length,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    def _load_or_encode(self):
        np = self._np
        if self.embedding_path.exists() and self.metadata_path.exists():
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            if metadata.get("asins") == self.asins:
                return np.load(self.embedding_path, mmap_mode="r")

        texts = [self._document_text(product) for product in self.catalog.products.values()]
        model = self._ensure_model()
        encoder = getattr(model, "encode_document", model.encode)
        embeddings = encoder(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")
        np.save(self.embedding_path, embeddings)
        self.metadata_path.write_text(
            json.dumps({"asins": self.asins, "shape": list(embeddings.shape)}),
            encoding="utf-8",
        )
        return embeddings

    def _document_text(self, product: dict[str, Any]) -> str:
        identity = "\n".join((
            f"Title: {_text(product.get('title'))}",
            f"Category: {_text(product.get('categories'))}",
            f"Brand: {_text(product.get('store'))}",
            f"Details: {_text(product.get('details'))}",
        ))
        semantic = "\n".join((
            f"Title: {_text(product.get('title'))}",
            f"Features: {_text(product.get('features'))}",
            f"Description: {_text(product.get('description'))}",
        ))
        if self.document_view == "identity":
            return identity
        if self.document_view == "semantic":
            return semantic
        return f"{identity}\n{semantic}"

    def _build_faiss_index(self):
        if not self.use_faiss:
            return None
        try:
            import faiss
        except ImportError:
            return None
        index = faiss.IndexFlatIP(int(self.embeddings.shape[1]))
        index.add(self._np.asarray(self.embeddings, dtype="float32"))
        return index

    def search(self, query: str, limit: int = 200) -> list[dict[str, Any]]:
        if not query.strip() or not self.asins:
            return []
        model = self._ensure_model()
        encoder = getattr(model, "encode_query", model.encode)
        query_vector = encoder(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")
        limit = min(max(int(limit), 1), len(self.asins))
        if self._faiss_index is not None:
            scores, indices = self._faiss_index.search(query_vector, limit)
            ranked = list(zip(indices[0].tolist(), scores[0].tolist()))
        else:
            if self.embeddings is None:  # pragma: no cover - defensive invariant
                raise RuntimeError("NumPy embeddings unavailable without a FAISS index")
            scores = self._np.asarray(self.embeddings) @ query_vector[0]
            indices = self._np.argpartition(scores, -limit)[-limit:]
            indices = indices[self._np.argsort(scores[indices])[::-1]]
            ranked = [(int(index), float(scores[index])) for index in indices]

        products = self.catalog.get_many([self.asins[index] for index, _ in ranked])
        for rank, (product, (_, score)) in enumerate(zip(products, ranked), start=1):
            product["dense_rank"] = rank
            product["dense_score"] = float(score)
            product["dense_model"] = self.model_name
        return products
