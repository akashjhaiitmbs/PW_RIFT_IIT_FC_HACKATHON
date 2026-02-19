"""
LLM Explanation Service — called ONCE per drug, only after all
deterministic risk logic is saved.  The LLM cannot alter risk_analyses.
"""
from __future__ import annotations
import time
import json
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_explanation import LLMExplanation
import uuid
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# ChromaDB RAG helper
# ---------------------------------------------------------------------------
def _rag_retrieve(drug: str, clinical_phenotype: str, gene: str) -> List[str]:
    """
    Retrieve top-3 context chunks from ChromaDB cpic_guidelines collection.
    Returns empty list if ChromaDB is unavailable.
    """
    try:
        import chromadb  # type: ignore

        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_collection(settings.CHROMA_COLLECTION)
        query = f"{drug} {clinical_phenotype} {gene} metabolism guideline"
        results = collection.query(query_texts=[query], n_results=3)
        docs = results.get("documents", [[]])[0]
        return docs if docs else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------
def _build_prompt(
    context_chunks: List[str],
    gene: str,
    diplotype: str,
    genetic_phenotype: str,
    clinical_phenotype: str,
    drug_name: str,
    risk_label: str,
    phenoconversion_occurred: bool,
    active_inhibitor: Optional[str],
) -> str:
    context_text = "\n\n".join(context_chunks) if context_chunks else "No guideline excerpts available."
    inhibitor_note = (
        f"active inhibitor: {active_inhibitor}" if active_inhibitor else "no active inhibitors"
    )

    return f"""SYSTEM:
You are PharmaGuard AI, a Clinical Pharmacogenomics assistant. You explain drug-gene interactions to healthcare providers. You must answer ONLY using the provided guideline excerpts. If information is not in the excerpts, say "Insufficient guideline data available."

Never recommend a specific prescription decision. Use language like "Guidelines suggest considering..." or "Evidence supports...".

CONTEXT (Retrieved CPIC Guidelines):
{context_text}

PATIENT DATA:
- Gene: {gene}
- Diplotype: {diplotype}
- Genetic Phenotype: {genetic_phenotype}
- Clinical Phenotype (after phenoconversion): {clinical_phenotype}
- Drug: {drug_name}
- Risk Label: {risk_label}
- Phenoconversion occurred: {phenoconversion_occurred} ({inhibitor_note})

USER:
Generate a clinical explanation with exactly these four sections:
1. SUMMARY: 1-2 sentence high-level alert for a clinician.
2. MECHANISM: Explain the biological reason why this drug-gene combination produces this risk.
3. GUIDELINE: State what the CPIC/FDA guideline recommends, citing from the provided context.
4. PHENOCONVERSION NOTE: If phenoconversion occurred, explain how {active_inhibitor or 'the inhibitor'} changed the effective phenotype. If not, write "Not applicable."
"""


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------
def _parse_llm_response(text: str) -> Dict[str, str]:
    sections = {
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
        # Find next marker
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
# LLM call
# ---------------------------------------------------------------------------
def _call_llm(prompt: str) -> Dict[str, Any]:
    """Call Ollama-compatible endpoint. Returns raw response dict."""
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    t0 = time.time()
    try:
        resp = httpx.post(settings.LLM_ENDPOINT, json=payload, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "text": data.get("response", ""),
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
            "generation_time_ms": elapsed_ms,
        }
    except Exception as exc:
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "text": f"LLM unavailable: {exc}",
            "prompt_tokens": None,
            "completion_tokens": None,
            "generation_time_ms": elapsed_ms,
        }


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
        # Step 1 — RAG
        chunks = _rag_retrieve(drug_name, clinical_phenotype, gene)

        # Step 2 — Prompt
        prompt = _build_prompt(
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

        # Step 3 — LLM call
        llm_resp = _call_llm(prompt)
        parsed = _parse_llm_response(llm_resp["text"])

        # Step 4 — Save
        record = LLMExplanation(
            id=uuid.uuid4(),
            risk_analysis_id=risk_analysis_id,
            summary=parsed["summary"],
            mechanism_explanation=parsed["mechanism"],
            guideline_quote=parsed["guideline"],
            phenoconversion_note=parsed["phenoconversion_note"],
            retrieved_context_chunks={"chunks": chunks},
            llm_model_used=settings.LLM_MODEL,
            prompt_tokens=llm_resp.get("prompt_tokens"),
            completion_tokens=llm_resp.get("completion_tokens"),
            generation_time_ms=llm_resp.get("generation_time_ms"),
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
