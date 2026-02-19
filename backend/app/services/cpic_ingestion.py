"""
CPIC RAG Ingestion Service
==========================
Fetches live guideline data from https://api.cpicpgx.org for every
supported drug, converts it to rich natural-language text chunks,
embeds them with Azure OpenAI embeddings, and upserts into ChromaDB.

Called once at application startup.  Skips gracefully if ChromaDB or
the CPIC API is unavailable.

CPIC API (PostgREST) endpoints used:
  GET /v1/drug?name=eq.<name>                     → drugid, guidelineid
  GET /v1/guideline?id=eq.<id>                    → guideline name, url, genes
  GET /v1/recommendation?guidelineid=eq.<id>      → per-phenotype recommendations
  GET /v1/gene?symbol=eq.<gene>                   → gene metadata
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CPIC_BASE = "https://api.cpicpgx.org/v1"

# ── Drug → CPIC guideline ID mapping (pre-looked-up so we don't need extra
#    API calls at startup — these are stable CPIC IDs).
DRUG_GUIDELINE_MAP: Dict[str, Dict[str, Any]] = {
    "codeine": {
        "guideline_id": 100416,
        "guideline_name": "CYP2D6 and Codeine",
        "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/",
        "genes": ["CYP2D6"],
        "drug_name_cpic": "codeine",
    },
    "warfarin": {
        "guideline_id": 100425,
        "guideline_name": "CYP2C9, VKORC1, CYP4F2 and Warfarin",
        "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-warfarin-and-cyp2c9-and-vkorc1/",
        "genes": ["CYP2C9", "VKORC1", "CYP4F2"],
        "drug_name_cpic": "warfarin",
    },
    "clopidogrel": {
        "guideline_id": 100411,
        "guideline_name": "CYP2C19 and Clopidogrel",
        "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-clopidogrel-and-cyp2c19/",
        "genes": ["CYP2C19"],
        "drug_name_cpic": "clopidogrel",
    },
    "simvastatin": {
        "guideline_id": 100423,
        "guideline_name": "SLCO1B1 and Simvastatin",
        "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/",
        "genes": ["SLCO1B1"],
        "drug_name_cpic": "simvastatin",
    },
    "azathioprine": {
        "guideline_id": 100418,
        "guideline_name": "TPMT, NUDT15 and Thiopurines",
        "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-thiopurines-and-tpmt/",
        "genes": ["TPMT", "NUDT15"],
        "drug_name_cpic": "azathioprine",
    },
    "fluorouracil": {
        "guideline_id": 100419,
        "guideline_name": "DPYD and Fluoropyrimidines",
        "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-fluoropyrimidines-and-dpyd/",
        "genes": ["DPYD"],
        "drug_name_cpic": "fluorouracil",
    },
}


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------
def _embedding_model_name() -> str:
    if settings.OPENAI_API_TYPE.lower() == "azure":
        return settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    return settings.OPENAI_EMBEDDING_MODEL


def _make_sync_openai_client():
    """Return synchronous openai client for embedding (ChromaDB uses sync)."""
    import openai  # type: ignore
    if settings.OPENAI_API_TYPE.lower() == "azure":
        return openai.AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY)


def _embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts using Azure OpenAI embeddings.
    Returns list of float vectors. Falls back to None on error.
    """
    client = _make_sync_openai_client()
    model = _embedding_model_name()
    # Batch in chunks of 100 (API limit)
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), 100):
        batch = texts[i : i + 100]
        response = client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([d.embedding for d in response.data])
    return all_embeddings


# ---------------------------------------------------------------------------
# CPIC API fetchers
# ---------------------------------------------------------------------------
async def _fetch_json(client: httpx.AsyncClient, url: str, params: Optional[Dict] = None) -> Any:
    try:
        resp = await client.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("CPIC API fetch failed for %s: %s", url, exc)
        return []


async def _fetch_recommendations(client: httpx.AsyncClient, guideline_id: int) -> List[Dict]:
    return await _fetch_json(
        client,
        f"{CPIC_BASE}/recommendation",
        params={
            "guidelineid": f"eq.{guideline_id}",
            "select": "id,drugrecommendation,implications,phenotypes,classification,lookupkey,comments,population",
        },
    )


async def _fetch_gene(client: httpx.AsyncClient, gene_symbol: str) -> Optional[Dict]:
    rows = await _fetch_json(
        client,
        f"{CPIC_BASE}/gene",
        params={
            "symbol": f"eq.{gene_symbol}",
            "select": "symbol,hgncid,ncbiid,lookupmethod,notesondiplotype,notesonallelenaming",
        },
    )
    return rows[0] if rows else None


async def _fetch_drug(client: httpx.AsyncClient, drug_name: str) -> Optional[Dict]:
    rows = await _fetch_json(
        client,
        f"{CPIC_BASE}/drug",
        params={"name": f"eq.{drug_name}"},
    )
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Chunk builders
# ---------------------------------------------------------------------------
def _chunk_id(text: str) -> str:
    """Stable deterministic ID based on content hash."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _build_guideline_chunk(drug: str, meta: Dict) -> Tuple[str, str]:
    """Top-level guideline overview chunk."""
    genes_str = ", ".join(meta["genes"])
    text = (
        f"CPIC Guideline: {meta['guideline_name']}\n"
        f"Drug: {drug.upper()}\n"
        f"Primary Gene(s): {genes_str}\n"
        f"Guideline URL: {meta['guideline_url']}\n"
        f"This CPIC guideline provides evidence-based dosing recommendations for {drug.upper()} "
        f"based on patient genotype in gene(s) {genes_str}. "
        f"The guideline covers phenotypes including Poor Metabolizer (PM), Intermediate Metabolizer (IM), "
        f"Normal Metabolizer (NM), Rapid Metabolizer (RM), and Ultrarapid Metabolizer (UM) where applicable."
    )
    return _chunk_id(text), text


def _build_recommendation_chunk(drug: str, meta: Dict, rec: Dict) -> Tuple[str, str]:
    """One chunk per recommendation row."""
    phenotypes = rec.get("phenotypes") or {}
    implications = rec.get("implications") or {}
    lookupkey = rec.get("lookupkey") or {}
    comments = rec.get("comments") or ""

    pheno_str = "; ".join(f"{g}: {p}" for g, p in phenotypes.items()) if phenotypes else "N/A"
    impl_str = "; ".join(f"{g}: {v}" for g, v in implications.items()) if implications else "N/A"
    score_str = "; ".join(f"{g}: {s}" for g, s in lookupkey.items()) if lookupkey else "N/A"

    text = (
        f"CPIC Recommendation — Drug: {drug.upper()}\n"
        f"Guideline: {meta['guideline_name']}\n"
        f"Phenotype(s): {pheno_str}\n"
        f"Activity Score(s): {score_str}\n"
        f"Gene Impact: {impl_str}\n"
        f"Classification: {rec.get('classification', 'Unknown')}\n"
        f"Population: {rec.get('population', 'general')}\n"
        f"Recommendation: {rec.get('drugrecommendation', '')}\n"
        + (f"Additional notes: {comments}" if comments and comments.lower() != "n/a" else "")
    )
    return _chunk_id(text), text


def _build_gene_chunk(gene_symbol: str, gene_data: Dict, drugs_using_gene: List[str]) -> Tuple[str, str]:
    """One chunk per gene with pharmacogenomic context."""
    drugs_str = ", ".join(d.upper() for d in drugs_using_gene)
    notes = gene_data.get("notesondiplotype") or gene_data.get("notesonallelenaming") or ""
    lookup = gene_data.get("lookupmethod", "ACTIVITY_SCORE")

    text = (
        f"Gene: {gene_symbol}\n"
        f"HGNC ID: {gene_data.get('hgncid', 'N/A')}\n"
        f"NCBI Gene ID: {gene_data.get('ncbiid', 'N/A')}\n"
        f"Lookup Method: {lookup}\n"
        f"Relevant Drugs: {drugs_str}\n"
        f"This gene is pharmacogenomically relevant for {drugs_str}. "
        f"CPIC uses the {lookup} method to assign phenotype for {gene_symbol}. "
        + (f"Notes: {notes}" if notes else "")
    )
    return _chunk_id(text), text


def _build_phenotype_summary_chunk(drug: str, meta: Dict, recs: List[Dict]) -> Tuple[str, str]:
    """Summary chunk listing all phenotype→recommendation mappings for a drug."""
    lines = [
        f"CPIC Summary — {drug.upper()} Phenotype-to-Recommendation Table",
        f"Guideline: {meta['guideline_name']} ({meta['guideline_url']})",
        f"Genes: {', '.join(meta['genes'])}",
        "",
    ]
    seen: set = set()
    for rec in recs:
        phenotypes = rec.get("phenotypes") or {}
        pheno_str = "; ".join(f"{g}: {p}" for g, p in phenotypes.items()) if phenotypes else "Unknown"
        recom = rec.get("drugrecommendation", "")
        classif = rec.get("classification", "")
        key = pheno_str + recom
        if key not in seen and recom:
            seen.add(key)
            lines.append(f"  [{classif}] {pheno_str} → {recom}")

    text = "\n".join(lines)
    return _chunk_id(text), text


# ---------------------------------------------------------------------------
# ChromaDB upserter
# ---------------------------------------------------------------------------
def _upsert_to_chroma(
    ids: List[str],
    texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict],
) -> None:
    import chromadb  # type: ignore

    client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    try:
        collection = client.get_collection(settings.CHROMA_COLLECTION)
    except Exception:
        collection = client.create_collection(
            settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    # Upsert in batches of 50
    for i in range(0, len(ids), 50):
        collection.upsert(
            ids=ids[i : i + 50],
            documents=texts[i : i + 50],
            embeddings=embeddings[i : i + 50],
            metadatas=metadatas[i : i + 50],
        )
    logger.info("ChromaDB upsert complete: %d chunks in '%s'", len(ids), settings.CHROMA_COLLECTION)


def _collection_needs_refresh() -> bool:
    """Return True if ChromaDB collection is absent or has fewer than 20 docs."""
    try:
        import chromadb  # type: ignore
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        try:
            col = client.get_collection(settings.CHROMA_COLLECTION)
            count = col.count()
            if count >= 20:
                logger.info(
                    "ChromaDB '%s' already has %d docs — skipping ingestion.",
                    settings.CHROMA_COLLECTION, count,
                )
                return False
        except Exception:
            pass
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def ingest_cpic_guidelines() -> None:
    """
    Fetch CPIC data for all supported drugs, build text chunks,
    embed them, and upsert into ChromaDB.

    Runs at application startup. Skips if:
      - ChromaDB is unreachable
      - openai package is missing
      - Collection already has ≥20 documents (already seeded)
    """
    if not _collection_needs_refresh():
        return

    logger.info("Starting CPIC guideline ingestion into ChromaDB…")

    all_ids: List[str] = []
    all_texts: List[str] = []
    all_metadatas: List[Dict] = []

    # Track which genes we've already fetched
    fetched_genes: Dict[str, Dict] = {}
    gene_to_drugs: Dict[str, List[str]] = {}

    async with httpx.AsyncClient() as client:
        for drug, meta in DRUG_GUIDELINE_MAP.items():
            logger.info("  → Fetching CPIC data for %s (guideline %d)…", drug.upper(), meta["guideline_id"])

            # 1. Guideline overview chunk
            cid, text = _build_guideline_chunk(drug, meta)
            all_ids.append(cid)
            all_texts.append(text)
            all_metadatas.append({"drug": drug.upper(), "type": "guideline", "genes": ",".join(meta["genes"])})

            # 2. Fetch recommendations
            recs = await _fetch_recommendations(client, meta["guideline_id"])
            logger.info("     %d recommendations fetched", len(recs))

            for rec in recs:
                cid, text = _build_recommendation_chunk(drug, meta, rec)
                all_ids.append(cid)
                all_texts.append(text)
                pheno = "; ".join(rec.get("phenotypes", {}).values()) if rec.get("phenotypes") else "unknown"
                all_metadatas.append({
                    "drug": drug.upper(),
                    "type": "recommendation",
                    "phenotype": pheno,
                    "classification": rec.get("classification", ""),
                    "genes": ",".join(meta["genes"]),
                })

            # 3. Phenotype summary chunk
            cid, text = _build_phenotype_summary_chunk(drug, meta, recs)
            all_ids.append(cid)
            all_texts.append(text)
            all_metadatas.append({"drug": drug.upper(), "type": "phenotype_summary", "genes": ",".join(meta["genes"])})

            # 4. Track genes for gene chunks
            for gene in meta["genes"]:
                gene_to_drugs.setdefault(gene, []).append(drug)
                if gene not in fetched_genes:
                    gene_data = await _fetch_gene(client, gene)
                    if gene_data:
                        fetched_genes[gene] = gene_data

    # 5. Gene chunks (one per unique gene)
    for gene, gene_data in fetched_genes.items():
        drugs_using = gene_to_drugs.get(gene, [])
        cid, text = _build_gene_chunk(gene, gene_data, drugs_using)
        all_ids.append(cid)
        all_texts.append(text)
        all_metadatas.append({
            "type": "gene",
            "gene": gene,
            "drugs": ",".join(d.upper() for d in drugs_using),
        })

    logger.info("Total chunks to embed: %d", len(all_texts))

    # 6. Embed all chunks
    try:
        embeddings = await asyncio.get_event_loop().run_in_executor(
            None, _embed_texts, all_texts
        )
    except Exception as exc:
        logger.error("Embedding failed: %s — RAG ingestion aborted.", exc)
        return

    # 7. Upsert into ChromaDB
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, _upsert_to_chroma, all_ids, all_texts, embeddings, all_metadatas
        )
        logger.info("✅ CPIC RAG ingestion complete — %d chunks stored.", len(all_ids))
    except Exception as exc:
        logger.error("ChromaDB upsert failed: %s", exc)
