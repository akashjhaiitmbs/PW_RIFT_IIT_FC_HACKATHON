"""
LLM Explanation Service — called ONCE per drug, only after all
deterministic risk logic is saved.  The LLM cannot alter risk_analyses.

Uses the OpenAI Python SDK (works with both Azure OpenAI and standard OpenAI).
Configure via app/config.py or .env:

  OPENAI_API_TYPE=azure                         # "azure" | "openai"
  AZURE_OPENAI_ENDPOINT=https://...             # Azure only
  AZURE_OPENAI_API_KEY=sk-...
  AZURE_OPENAI_API_VERSION=2025-01-01-preview
  AZURE_OPENAI_DEPLOYMENT=gpt-5                 # deployment name in Azure
"""
from __future__ import annotations
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_explanation import LLMExplanation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Build the OpenAI client (Azure OR standard OpenAI)
# ---------------------------------------------------------------------------
def _make_client():
    """Return an openai.AsyncAzureOpenAI or openai.AsyncOpenAI client."""
    try:
        import openai  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "openai package not installed. Run: pip install openai"
        ) from exc

    if settings.OPENAI_API_TYPE.lower() == "azure":
        return openai.AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    else:
        return openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _model_name() -> str:
    """Return the model/deployment name to pass to the API."""
    if settings.OPENAI_API_TYPE.lower() == "azure":
        return settings.AZURE_OPENAI_DEPLOYMENT
    return settings.OPENAI_MODEL


# ---------------------------------------------------------------------------
# ChromaDB RAG helper  (semantic search via embeddings)
# ---------------------------------------------------------------------------
def _rag_retrieve(drug: str, clinical_phenotype: str, gene: str) -> List[str]:
    """
    Embed the query and do a cosine-similarity search against the
    ChromaDB cpic_guidelines collection.
    Returns top-5 relevant text chunks, filtered to the drug where possible.
    Falls back to empty list if ChromaDB or embeddings are unavailable.
    """
    try:
        import chromadb  # type: ignore
        from app.services.cpic_ingestion import _make_sync_openai_client, _embedding_model_name

        # Build a rich query that captures the clinical context
        query = (
            f"{drug} {gene} {clinical_phenotype} metabolism guideline "
            f"dosing recommendation phenoconversion CPIC"
        )

        # Embed the query
        oa_client = _make_sync_openai_client()
        embed_resp = oa_client.embeddings.create(
            model=_embedding_model_name(),
            input=[query],
        )
        query_embedding = embed_resp.data[0].embedding

        # Query ChromaDB with vector + optional drug filter
        chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        collection = chroma_client.get_collection(settings.CHROMA_COLLECTION)

        # Try drug-filtered search first (more relevant)
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                where={"drug": drug.upper()},
            )
            docs = results.get("documents", [[]])[0]
            if docs:
                return docs
        except Exception:
            pass

        # Fall back to unfiltered search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
        )
        docs = results.get("documents", [[]])[0]
        return docs if docs else []

    except Exception as exc:
        logger.warning("RAG retrieval failed (non-fatal): %s", exc)
        return []


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------
def _build_messages(
    context_chunks: List[str],
    gene: str,
    diplotype: str,
    genetic_phenotype: str,
    clinical_phenotype: str,
    drug_name: str,
    risk_label: str,
    phenoconversion_occurred: bool,
    active_inhibitor: Optional[str],
) -> List[Dict[str, str]]:
    context_text = "\n\n".join(context_chunks) if context_chunks else "No guideline excerpts available."
    inhibitor_note = (
        f"active inhibitor: {active_inhibitor}" if active_inhibitor else "no active inhibitors"
    )

    system_prompt = (
        "You are PharmaGuard AI, a Clinical Pharmacogenomics assistant. "
        "You explain drug-gene interactions to healthcare providers. "
        "You must answer ONLY using the provided guideline excerpts. "
        "If information is not in the excerpts, say \"Insufficient guideline data available.\"\n\n"
        "Never recommend a specific prescription decision. "
        "Use language like \"Guidelines suggest considering...\" or \"Evidence supports...\"."
    )

    user_prompt = f"""CONTEXT (Retrieved CPIC Guidelines):
{context_text}

PATIENT DATA:
- Gene: {gene}
- Diplotype: {diplotype}
- Genetic Phenotype: {genetic_phenotype}
- Clinical Phenotype (after phenoconversion): {clinical_phenotype}
- Drug: {drug_name}
- Risk Label: {risk_label}
- Phenoconversion occurred: {phenoconversion_occurred} ({inhibitor_note})

Generate a clinical explanation with exactly these four sections:
1. SUMMARY: 1-2 sentence high-level alert for a clinician.
2. MECHANISM: Explain the biological reason why this drug-gene combination produces this risk.
3. GUIDELINE: State what the CPIC/FDA guideline recommends, citing from the provided context.
4. PHENOCONVERSION NOTE: If phenoconversion occurred, explain how {active_inhibitor or 'the inhibitor'} changed the effective phenotype. If not, write "Not applicable."
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------
def _parse_llm_response(text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {
        "summary": "",
        "mechanism": "",
        "guideline": "",
        "phenoconversion_note": "",
    }
    markers = [
        ("SUMMARY:", "summary"),
        ("MECHANISM:", "mechanism"),
        ("GUIDELINE:", "guideline"),
        ("PHENOCONVERSION NOTE:", "phenoconversion_note"),
    ]
    remaining = text
    for i, (marker, key) in enumerate(markers):
        upper = remaining.upper()
        idx = upper.find(marker)
        if idx == -1:
            continue
        start = idx + len(marker)
        next_idx = len(remaining)
        for j, (next_marker, _) in enumerate(markers):
            if j <= i:
                continue
            ni = upper.find(next_marker, start)
            if ni != -1 and ni < next_idx:
                next_idx = ni
        sections[key] = remaining[start:next_idx].strip()
        remaining = remaining[next_idx:]
    return sections


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
class LLMExplainer:
    async def explain_and_save(
        self,
        db: AsyncSession,
        risk_analysis_id: uuid.UUID,
        gene: str,
        diplotype: str,
        genetic_phenotype: str,
        clinical_phenotype: str,
        drug_name: str,
        risk_label: str,
        phenoconversion_occurred: bool,
        active_inhibitor: Optional[str],
    ) -> LLMExplanation:
        # Step 1 — RAG (optional; graceful no-op if ChromaDB unavailable)
        chunks = _rag_retrieve(drug_name, clinical_phenotype, gene)

        # Step 2 — Build chat messages
        messages = _build_messages(
            context_chunks=chunks,
            gene=gene,
            diplotype=diplotype or "Unknown",
            genetic_phenotype=genetic_phenotype or "Unknown",
            clinical_phenotype=clinical_phenotype or "Unknown",
            drug_name=drug_name,
            risk_label=risk_label or "Unknown",
            phenoconversion_occurred=phenoconversion_occurred,
            active_inhibitor=active_inhibitor,
        )

        # Step 3 — Call LLM via OpenAI SDK
        raw_text = ""
        prompt_tokens: Optional[int] = None
        completion_tokens: Optional[int] = None
        generation_time_ms: int = 0
        model_used = f"{settings.OPENAI_API_TYPE}:{_model_name()}"

        t0 = time.time()
        try:
            client = _make_client()
            response = await client.chat.completions.create(
                model=_model_name(),
                messages=messages,  # type: ignore[arg-type]
                temperature=0.3,
                max_tokens=800,
            )
            generation_time_ms = int((time.time() - t0) * 1000)
            raw_text = response.choices[0].message.content or ""
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
        except Exception as exc:
            generation_time_ms = int((time.time() - t0) * 1000)
            raw_text = f"LLM unavailable: {exc}"

        # Step 4 — Parse sections
        parsed = _parse_llm_response(raw_text)

        # Step 5 — Persist
        record = LLMExplanation(
            id=uuid.uuid4(),
            risk_analysis_id=risk_analysis_id,
            summary=parsed["summary"] or raw_text[:500],
            mechanism_explanation=parsed["mechanism"],
            guideline_quote=parsed["guideline"],
            phenoconversion_note=parsed["phenoconversion_note"],
            retrieved_context_chunks={"chunks": chunks},
            llm_model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            generation_time_ms=generation_time_ms,
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
