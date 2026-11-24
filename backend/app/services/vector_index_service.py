"""
Vector Index Service for KGraph Chat RAG.

Builds a ChromaDB collection from the software CSV using Ollama
`nomic-embed-text` embeddings. Provides semantic similarity search
to replace the previous naive keyword-matching retrieval.

Flow:
  startup → build_index()
    ├── reads software_knowledge_graph_data.csv
    ├── converts each row to a rich text string
    ├── calls Ollama /api/embeddings (nomic-embed-text) for each row
    └── upserts vectors + metadata into ChromaDB (persisted to disk)

  query(text, top_k) →
    ├── embeds the query text via nomic-embed-text
    ├── performs cosine similarity search in ChromaDB
    └── returns top_k CSV row dicts (passed as context to the LLM)
"""

import os
import csv
import json
import logging
import hashlib
import httpx
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_URL",         "http://localhost:11434")
EMBED_MODEL   = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_PATH   = os.getenv("CHROMA_PATH",        "/app/chroma_db")
COLLECTION    = "kgraph_software"
EMBED_BATCH   = 8       # rows to embed per batch
EMBED_TIMEOUT = 60.0    # seconds per embedding call

# Fingerprint stored as a sidecar JSON file — avoids deleting the collection
FINGERPRINT_FILE = os.path.join(CHROMA_PATH, ".index_fingerprint.json")

CSV_PATHS = [
    "/app/software_knowledge_graph_data.csv",
    "software_knowledge_graph_data.csv",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "software_knowledge_graph_data.csv",
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_text(row: Dict[str, Any]) -> str:
    """
    Compose a semantically rich text string from a CSV row.
    Field order: high-signal fields first so the embedding weights them more.
    """
    parts: List[str] = []
    if row.get("Software Name"):
        parts.append(f"Software: {row['Software Name']}.")
    if row.get("Short Description"):
        parts.append(f"Description: {row['Short Description']}.")
    if row.get("Categories"):
        parts.append(f"Category: {row['Categories']}.")
    if row.get("Technologies"):
        parts.append(f"Technologies: {row['Technologies']}.")
    if row.get("Workcenters"):
        parts.append(f"Location: {row['Workcenters']}.")
    if row.get("Developer Names"):
        parts.append(f"Developers: {row['Developer Names']}.")
    if row.get("Developer Group"):
        parts.append(f"Group: {row['Developer Group']}.")
    if row.get("Detailed Description"):
        detail = str(row["Detailed Description"])[:400]
        parts.append(f"Details: {detail}.")
    return " ".join(parts)


def _csv_fingerprint(rows: List[Dict]) -> str:
    """MD5 of all software names — detects CSV row additions/removals."""
    names = "|".join(str(r.get("Software Name", "")) for r in rows)
    return hashlib.md5(names.encode()).hexdigest()


def _load_stored_fingerprint() -> str | None:
    """Read the fingerprint saved from the last successful index build."""
    try:
        if os.path.exists(FINGERPRINT_FILE):
            with open(FINGERPRINT_FILE) as f:
                data = json.load(f)
                return data.get("fingerprint")
    except Exception:
        pass
    return None


def _save_fingerprint(fingerprint: str):
    """Persist the fingerprint after a successful index build."""
    os.makedirs(os.path.dirname(FINGERPRINT_FILE), exist_ok=True)
    with open(FINGERPRINT_FILE, "w") as f:
        json.dump({"fingerprint": fingerprint}, f)


def _find_csv() -> str:
    for p in CSV_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        f"software_knowledge_graph_data.csv not found. Searched: {CSV_PATHS}"
    )


def _read_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Strip whitespace from all string values
    return [{k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            for row in rows]


# ── Embedding ─────────────────────────────────────────────────────────────────

async def _embed(text: str) -> List[float]:
    """Call Ollama /api/embeddings for a single text string."""
    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT) as client:
        res = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
        )
        res.raise_for_status()
        data = res.json()
        vec = data.get("embedding")
        if not vec:
            raise ValueError(f"Ollama returned no embedding. Response: {data}")
        return vec


async def _embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts sequentially (Ollama is single-threaded per model)."""
    return [await _embed(text) for text in texts]


# ── VectorIndexService ────────────────────────────────────────────────────────

class VectorIndexService:
    """
    Persistent ChromaDB vector index over the KGraph software CSV.

    Lifecycle:
      - Call `await build_index()` once at application startup.
      - Use `await query(text, top_k)` for semantic similarity search.

    Fingerprint stored in FINGERPRINT_FILE (sidecar JSON) — NOT in ChromaDB
    collection metadata. This avoids the destructive delete/recreate pattern
    that would wipe indexed data just to store metadata.
    """

    def __init__(self):
        self._ready = False
        self._chroma: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    def _init_chroma(self):
        """Lazily initialise ChromaDB PersistentClient."""
        os.makedirs(CHROMA_PATH, exist_ok=True)
        self._chroma = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._chroma.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"VectorIndex: ChromaDB initialised at {CHROMA_PATH!r}")

    async def build_index(self):
        """
        Read CSV → embed rows → upsert into ChromaDB.

        Skip logic:
          - Reads fingerprint from FINGERPRINT_FILE (plain JSON sidecar).
          - If fingerprint matches AND collection count == len(rows): skip.
          - Otherwise: wipe collection and re-index from scratch.

        The fingerprint is saved ONLY after all rows are successfully upserted,
        so a partial/failed index build will always trigger a full re-index on
        the next startup.
        """
        logger.info("VectorIndex: starting index build check...")
        self._init_chroma()

        csv_path = _find_csv()
        rows = _read_csv(csv_path)
        if not rows:
            logger.error("VectorIndex: CSV is empty — aborting.")
            return

        current_fp   = _csv_fingerprint(rows)
        stored_fp    = _load_stored_fingerprint()
        stored_count = self._collection.count()

        if stored_count == len(rows) and stored_fp == current_fp:
            logger.info(
                f"VectorIndex: ✅ already indexed {stored_count} rows "
                f"(fingerprint match). Skipping."
            )
            self._ready = True
            return

        # Data has changed or index is incomplete — wipe and re-index
        if stored_count > 0:
            logger.info(
                f"VectorIndex: stale index (stored={stored_count}, "
                f"current={len(rows)}, fp_match={stored_fp == current_fp}). "
                "Wiping and re-indexing..."
            )
            self._chroma.delete_collection(COLLECTION)
            self._collection = self._chroma.create_collection(
                name=COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )

        logger.info(f"VectorIndex: embedding {len(rows)} rows from {csv_path!r}...")
        total = len(rows)

        for batch_start in range(0, total, EMBED_BATCH):
            batch_rows  = rows[batch_start : batch_start + EMBED_BATCH]
            batch_texts = [_row_to_text(r) for r in batch_rows]

            try:
                embeddings = await _embed_batch(batch_texts)
            except Exception as e:
                logger.error(
                    f"VectorIndex: embedding failed for rows "
                    f"{batch_start}–{batch_start + len(batch_rows) - 1}: {e}"
                )
                raise

            # Sanitise metadata: ChromaDB requires str/int/float/bool values only
            sanitised = [
                {k: (str(v) if v is not None else "") for k, v in row.items()}
                for row in batch_rows
            ]

            self._collection.upsert(
                ids=[f"row_{batch_start + j}" for j in range(len(batch_rows))],
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=sanitised,
            )
            logger.info(
                f"VectorIndex: upserted rows {batch_start}–"
                f"{batch_start + len(batch_rows) - 1} / {total}"
            )

        # ✅ All rows upserted — save fingerprint as sidecar file (NOT via
        # collection delete/recreate which would wipe the indexed data!)
        _save_fingerprint(current_fp)
        logger.info(f"VectorIndex: ✅ index build complete — {total} rows indexed.")
        self._ready = True

    async def query(
        self,
        query_text: str,
        top_k: int = 6,
        distance_threshold: float = 0.75,
    ) -> List[Dict[str, Any]]:
        """
        Embed `query_text` and return top_k most semantically similar CSV rows.

        Only rows with cosine distance <= distance_threshold are returned.
        If none pass the threshold the top-3 candidates are returned anyway
        so the caller (chat_rag_service) can apply its own grounding check.

        Returns [] (with warning) if index is not ready.
        """
        if not self._ready or self._collection is None:
            logger.warning("VectorIndex: not ready — returning empty context.")
            return []

        collection_count = self._collection.count()
        if collection_count == 0:
            logger.warning("VectorIndex: collection is empty — returning empty context.")
            return []

        try:
            query_vec = await _embed(query_text)
        except Exception as e:
            logger.error(f"VectorIndex: query embedding failed: {e}")
            return []

        n = min(top_k, collection_count)
        try:
            results = self._collection.query(
                query_embeddings=[query_vec],
                n_results=n,
                include=["metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"VectorIndex: ChromaDB query failed: {e}")
            return []

        metadatas: List[Dict] = results.get("metadatas", [[]])[0]
        distances: List[float] = results.get("distances",  [[]])[0]

        logger.info(
            f"VectorIndex: query={query_text!r} → "
            f"top distances={[round(d, 4) for d in distances]}"
        )

        # Keep only results within the relevance threshold
        filtered = [
            meta
            for meta, dist in zip(metadatas, distances)
            if dist <= distance_threshold
        ]

        if filtered:
            logger.info(
                f"VectorIndex: {len(filtered)}/{len(metadatas)} results "
                f"within distance_threshold={distance_threshold}"
            )
            return filtered

        # Nothing passed the threshold — return top-3 as weak candidates
        # (caller will apply a grounding check and may fall back to direct RAG)
        logger.warning(
            f"VectorIndex: no results within threshold={distance_threshold}; "
            f"returning top 3 weak candidates."
        )
        return metadatas[:3]


# ── Singleton ─────────────────────────────────────────────────────────────────

vector_index = VectorIndexService()
