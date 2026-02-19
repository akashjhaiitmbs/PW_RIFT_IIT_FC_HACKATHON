"""
POST /api/v1/analyze
Runs the full synchronous PGx pipeline and returns results immediately.
No Celery/Redis — everything happens in-request.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vcf_upload import VCFUpload
from app.models.analysis_request import AnalysisRequest
from app.services.cpic_engine import SUPPORTED_DRUGS
from app.services.pipeline import run_analysis_pipeline
from app.schemas.schemas import AnalyzeRequest, APIResponse, DrugResultSchema

router = APIRouter()


@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    # ── 1. Validate vcf_upload_id ─────────────────────────────────────────
    vcf_upload: VCFUpload | None = await db.get(VCFUpload, body.vcf_upload_id)
    if not vcf_upload:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "data": None, "error": "VCF upload not found"},
        )
    if vcf_upload.parsing_status != "success":
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "data": None,
                "error": f"VCF parsing status is '{vcf_upload.parsing_status}', must be 'success'",
            },
        )

    # ── 2. Validate drugs ─────────────────────────────────────────────────
    bad_drugs = [d for d in body.drugs if d.upper() not in SUPPORTED_DRUGS]
    if bad_drugs:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "data": None,
                "error": f"Unsupported drugs: {bad_drugs}. Supported: {SUPPORTED_DRUGS}",
            },
        )

    # ── 3. Create analysis_request record ─────────────────────────────────
    now = datetime.now(timezone.utc)
    req = AnalysisRequest(
        id=uuid.uuid4(),
        patient_id=vcf_upload.patient_id,
        vcf_upload_id=body.vcf_upload_id,
        requested_drugs=[d.upper() for d in body.drugs],
        concurrent_medications=[m.upper() for m in body.concurrent_medications],
        status="processing",
        created_at=now,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    # ── 4. Run full pipeline synchronously ────────────────────────────────
    try:
        results = await run_analysis_pipeline(
            analysis_request_id=req.id,
            db=db,
        )
    except Exception as exc:
        return {
            "success": False,
            "data": None,
            "error": str(exc),
        }

    return {
        "success": True,
        "data": {
            "analysis_request_id": str(req.id),
            "status": "complete",
            "results": results,
        },
        "error": None,
    }
