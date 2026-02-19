"""
GET /api/v1/results/{analysis_request_id}
Returns full structured results for a completed analysis.
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.analysis_request import AnalysisRequest
from app.models.risk_analysis import RiskAnalysis
from app.models.llm_explanation import LLMExplanation
from app.models.detected_variant import DetectedVariant
from app.models.vcf_upload import VCFUpload
from app.models.patient import Patient
from app.models.pgx_genotype_call import PGxGenotypeCall
from app.services.pipeline import _build_result
from datetime import datetime, timezone

router = APIRouter()


@router.get("/results/{analysis_request_id}")
async def get_results(
    analysis_request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    req: AnalysisRequest | None = await db.get(AnalysisRequest, analysis_request_id)
    if not req:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "data": None, "error": "Analysis request not found"},
        )
    if req.status != "complete":
        return {
            "success": True,
            "data": {"status": req.status, "results": []},
            "error": None,
        }

    # Load all risk rows for this request
    risk_stmt = select(RiskAnalysis).where(
        RiskAnalysis.vcf_upload_id == req.vcf_upload_id,
        RiskAnalysis.patient_id == req.patient_id,
    )
    risk_rows = (await db.execute(risk_stmt)).scalars().all()

    vcf_upload: VCFUpload = await db.get(VCFUpload, req.vcf_upload_id)
    patient: Patient = await db.get(Patient, req.patient_id)

    # Gene calls for quality metrics
    gene_stmt = select(PGxGenotypeCall).where(
        PGxGenotypeCall.vcf_upload_id == req.vcf_upload_id
    )
    gene_calls = (await db.execute(gene_stmt)).scalars().all()
    genes_ok = [c.gene for c in gene_calls if (c.phenotype or "") != "Unknown"]
    genes_failed = [c.gene for c in gene_calls if (c.phenotype or "") == "Unknown"]

    results = []
    for risk_row in risk_rows:
        if risk_row.drug_name not in (req.requested_drugs or []):
            continue

        # LLM explanation
        llm_stmt = select(LLMExplanation).where(
            LLMExplanation.risk_analysis_id == risk_row.id
        )
        llm_rec = (await db.execute(llm_stmt)).scalars().first()

        # Gene variants
        primary_gene_base = (risk_row.primary_gene or "").split("+")[0]
        var_stmt = select(DetectedVariant).where(
            DetectedVariant.vcf_upload_id == req.vcf_upload_id,
            DetectedVariant.gene == primary_gene_base,
        )
        gene_variants = (await db.execute(var_stmt)).scalars().all()
        variant_dicts = [
            {
                "rsid": v.rsid,
                "gene": v.gene,
                "position": v.position,
                "ref_allele": v.ref_allele,
                "alt_allele": v.alt_allele,
                "genotype": v.genotype,
                "star_allele": v.star_allele,
                "filter_status": v.filter_status,
            }
            for v in gene_variants
        ]

        results.append(
            _build_result(
                patient=patient,
                drug=risk_row.drug_name,
                risk_row=risk_row,
                llm_rec=llm_rec,
                gene_variants=variant_dicts,
                vcf_upload=vcf_upload,
                genes_called_ok=genes_ok,
                genes_failed=genes_failed,
            )
        )

    return {
        "success": True,
        "data": results if len(results) > 1 else (results[0] if results else {}),
        "error": None,
    }


@router.get("/status/{analysis_request_id}")
async def get_status(
    analysis_request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    req: AnalysisRequest | None = await db.get(AnalysisRequest, analysis_request_id)
    if not req:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "data": None, "error": "Analysis request not found"},
        )
    return {
        "success": True,
        "data": {
            "analysis_request_id": str(req.id),
            "status": req.status,
            "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        },
        "error": None,
    }
