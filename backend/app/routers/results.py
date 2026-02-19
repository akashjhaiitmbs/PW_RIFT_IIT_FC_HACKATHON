"""
GET /api/v1/results/{patient_id}
Returns all completed analysis results for a patient.
Accepts either:
  - A UUID  → looked up as Patient.id
  - A string → looked up as Patient.patient_code
"""
from __future__ import annotations

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

router = APIRouter()


@router.get("/results/{patient_id}")
async def get_results(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all completed analysis results for a patient.
    `patient_id` can be either:
      - A UUID (Patient.id)
      - A patient code string (Patient.patient_code)
    """

    # ── 1. Resolve patient ────────────────────────────────────────────────────
    patient: Patient | None = None

    # Try UUID first
    import uuid as _uuid
    try:
        pid = _uuid.UUID(patient_id)
        patient = await db.get(Patient, pid)
    except ValueError:
        pass

    # Fall back to patient_code lookup
    if not patient:
        stmt = select(Patient).where(Patient.patient_code == patient_id)
        patient = (await db.execute(stmt)).scalars().first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "data": None, "error": f"Patient '{patient_id}' not found"},
        )

    # ── 2. Load all completed analysis requests for this patient ──────────────
    req_stmt = (
        select(AnalysisRequest)
        .where(
            AnalysisRequest.patient_id == patient.id,
            AnalysisRequest.status == "complete",
        )
        .order_by(AnalysisRequest.created_at.desc())
    )
    requests = (await db.execute(req_stmt)).scalars().all()

    if not requests:
        # Check if there are any requests at all (might still be processing)
        any_stmt = select(AnalysisRequest).where(AnalysisRequest.patient_id == patient.id)
        any_req = (await db.execute(any_stmt)).scalars().first()
        if any_req:
            return {
                "success": True,
                "data": {
                    "patient_id": str(patient.id),
                    "patient_code": patient.patient_code,
                    "status": any_req.status,
                    "results": [],
                },
                "error": None,
            }
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "data": None,
                "error": f"No analysis results found for patient '{patient_id}'",
            },
        )

    # ── 3. Assemble results from most-recent analysis request ─────────────────
    # Use the most recent completed request
    req = requests[0]

    vcf_upload: VCFUpload = await db.get(VCFUpload, req.vcf_upload_id)

    # Gene calls for quality metrics
    gene_stmt = select(PGxGenotypeCall).where(
        PGxGenotypeCall.vcf_upload_id == req.vcf_upload_id
    )
    gene_calls = (await db.execute(gene_stmt)).scalars().all()
    genes_ok = [c.gene for c in gene_calls if (c.phenotype or "") != "Unknown"]
    genes_failed = [c.gene for c in gene_calls if (c.phenotype or "") == "Unknown"]

    # Risk rows for this request
    risk_stmt = select(RiskAnalysis).where(
        RiskAnalysis.vcf_upload_id == req.vcf_upload_id,
        RiskAnalysis.patient_id == patient.id,
    )
    risk_rows = (await db.execute(risk_stmt)).scalars().all()

    results = []
    for risk_row in risk_rows:
        if risk_row.drug_name not in (req.requested_drugs or []):
            continue

        # LLM explanation
        llm_stmt = select(LLMExplanation).where(
            LLMExplanation.risk_analysis_id == risk_row.id
        )
        llm_rec = (await db.execute(llm_stmt)).scalars().first()

        # Gene variants for this drug
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
        "data": {
            "patient_id": str(patient.id),
            "patient_code": patient.patient_code,
            "analysis_request_id": str(req.id),
            "status": req.status,
            "completed_at": req.completed_at.isoformat() if req.completed_at else None,
            "total_variants_parsed": vcf_upload.total_variants_found if vcf_upload else 0,
            "results": results,
        },
        "error": None,
    }
