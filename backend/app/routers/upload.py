"""
POST /api/v1/upload
Upload a VCF file, parse it synchronously, persist variants.
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.patient import Patient
from app.models.vcf_upload import VCFUpload
from app.models.detected_variant import DetectedVariant
from app.services.vcf_parser import VCFParser
from app.schemas.schemas import APIResponse, UploadResponse

router = APIRouter()

MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=APIResponse[UploadResponse])
async def upload_vcf(
    vcf_file: UploadFile = File(...),
    patient_code: str = Form(default="PATIENT_UNKNOWN"),
    db: AsyncSession = Depends(get_db),
):
    # ── 1. Validate file ──────────────────────────────────────────────────
    if not vcf_file.filename.endswith(".vcf"):
        raise HTTPException(
            status_code=400,
            detail={"success": False, "data": None, "error": "Only .vcf files are accepted"},
        )

    content = await vcf_file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "data": None,
                "error": f"File exceeds {settings.MAX_FILE_SIZE_MB} MB limit",
            },
        )

    # ── 2. Get or create patient ──────────────────────────────────────────
    stmt = select(Patient).where(Patient.patient_code == patient_code)
    patient: Patient | None = (await db.execute(stmt)).scalars().first()
    if not patient:
        patient = Patient(
            id=uuid.uuid4(),
            patient_code=patient_code,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(patient)
        await db.flush()

    # ── 3. Save file to disk ──────────────────────────────────────────────
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(patient.id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, vcf_file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # ── 4. Create vcf_uploads record ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    vcf_upload = VCFUpload(
        id=uuid.uuid4(),
        patient_id=patient.id,
        filename=vcf_file.filename,
        file_path=file_path,
        file_size_bytes=len(content),
        parsing_status="processing",
        created_at=now,
        updated_at=now,
    )
    db.add(vcf_upload)
    await db.flush()

    # ── 5. Parse VCF synchronously ────────────────────────────────────────
    parser = VCFParser()
    parse_result = parser.parse(file_path)

    if not parse_result.success:
        vcf_upload.parsing_status = "failed"
        vcf_upload.parsing_error = parse_result.error
        await db.commit()
        return APIResponse(
            success=False,
            data=None,
            error=parse_result.error,
        )

    vcf_upload.parsing_status = "success"
    vcf_upload.vcf_version = parse_result.vcf_version
    vcf_upload.total_variants_found = parse_result.total_variants
    vcf_upload.updated_at = datetime.now(timezone.utc)

    # ── 6. Save detected variants ─────────────────────────────────────────
    genes_seen: set[str] = set()
    for v in parse_result.variants:
        if v.get("gene"):
            genes_seen.add(v["gene"])
        dv = DetectedVariant(
            id=uuid.uuid4(),
            vcf_upload_id=vcf_upload.id,
            patient_id=patient.id,
            rsid=v.get("rsid"),
            gene=v.get("gene"),
            chromosome=v.get("chromosome"),
            position=v.get("position"),
            ref_allele=v.get("ref_allele"),
            alt_allele=v.get("alt_allele"),
            genotype=v.get("genotype"),
            star_allele=v.get("star_allele"),
            quality_score=v.get("quality_score"),
            filter_status=v.get("filter_status"),
            created_at=now,
        )
        db.add(dv)

    await db.commit()

    return APIResponse(
        success=True,
        data=UploadResponse(
            vcf_upload_id=vcf_upload.id,
            patient_id=patient.id,
            patient_code=patient.patient_code,
            parsing_status="success",
            total_variants_found=parse_result.total_variants,
            genes_detected=sorted(genes_seen),
        ),
    )
