"""
POST /api/v1/analyze
Single consolidated route: accepts VCF file + patient info + drug list,
runs the full pipeline, and returns results immediately.

Steps internally:
  1. Validate & save the VCF file
  2. Get or create Patient record
  3. Parse VCF synchronously
  4. Run full PGx pipeline (genotyping → risk → LLM explanation)
  5. Return complete results
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models.patient import Patient
from app.models.vcf_upload import VCFUpload
from app.models.detected_variant import DetectedVariant
from app.models.analysis_request import AnalysisRequest
from app.services.vcf_parser import VCFParser
from app.services.cpic_engine import SUPPORTED_DRUGS
from app.services.pipeline import run_analysis_pipeline
from sqlalchemy import select

router = APIRouter()

MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/analyze")
async def analyze(
    vcf_file: UploadFile = File(..., description="Genomic VCF file (.vcf)"),
    patient_code: str = Form(default="PATIENT_001", description="Unique patient identifier"),
    drugs: str = Form(..., description="Comma-separated list of drugs, e.g. CODEINE,WARFARIN"),
    concurrent_medications: str = Form(
        default="",
        description="Comma-separated list of co-medications for phenoconversion, e.g. PAROXETINE,FLUOXETINE",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Full analysis in one shot:
    - Upload & parse VCF
    - Run PGx pipeline for the requested drugs
    - Return structured risk + LLM explanation results
    """

    # ── 1. Validate file ──────────────────────────────────────────────────────
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

    # ── 2. Parse & validate drug list ─────────────────────────────────────────
    drug_list: List[str] = [d.strip().upper() for d in drugs.split(",") if d.strip()]
    if not drug_list:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "data": None, "error": "At least one drug must be specified"},
        )

    bad_drugs = [d for d in drug_list if d not in SUPPORTED_DRUGS]
    if bad_drugs:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "data": None,
                "error": f"Unsupported drugs: {bad_drugs}. Supported: {list(SUPPORTED_DRUGS)}",
            },
        )

    med_list: List[str] = [m.strip().upper() for m in concurrent_medications.split(",") if m.strip()]

    # ── 3. Get or create Patient ───────────────────────────────────────────────
    stmt = select(Patient).where(Patient.patient_code == patient_code)
    patient: Optional[Patient] = (await db.execute(stmt)).scalars().first()
    if not patient:
        patient = Patient(
            id=uuid.uuid4(),
            patient_code=patient_code,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(patient)
        await db.flush()

    # ── 4. Save file to disk ───────────────────────────────────────────────────
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(patient.id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, vcf_file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # ── 5. Create VCFUpload record ─────────────────────────────────────────────
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

    # ── 6. Parse VCF synchronously ─────────────────────────────────────────────
    parser = VCFParser()
    parse_result = parser.parse(file_path)

    if not parse_result.success:
        vcf_upload.parsing_status = "failed"
        vcf_upload.parsing_error = parse_result.error
        await db.commit()
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "data": None,
                "error": f"VCF parsing failed: {parse_result.error}",
            },
        )

    vcf_upload.parsing_status = "success"
    vcf_upload.vcf_version = parse_result.vcf_version
    vcf_upload.total_variants_found = parse_result.total_variants
    vcf_upload.updated_at = datetime.now(timezone.utc)

    # ── 7. Save detected variants ──────────────────────────────────────────────
    for v in parse_result.variants:
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

    # ── 8. Create AnalysisRequest ──────────────────────────────────────────────
    req = AnalysisRequest(
        id=uuid.uuid4(),
        patient_id=patient.id,
        vcf_upload_id=vcf_upload.id,
        requested_drugs=drug_list,
        concurrent_medications=med_list,
        status="processing",
        created_at=now,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    # ── 9. Run full pipeline synchronously ─────────────────────────────────────
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

    # ── 10. Build gene_panel (unique genes across all drug results) ────────────
    gene_panel = _build_gene_panel(results)

    return {
        "success": True,
        "data": {
            "patient_id": str(patient.id),
            "patient_code": patient.patient_code,
            "analysis_request_id": str(req.id),
            "vcf_upload_id": str(vcf_upload.id),
            "total_variants_parsed": parse_result.total_variants,
            "status": "complete",
            "gene_panel": gene_panel,
            "results": results,
        },
        "error": None,
    }


# ── helpers ────────────────────────────────────────────────────────────────────

_PHENOTYPE_SUMMARIES = {
    "PM": "cannot metabolize {gene} substrates effectively — enzyme activity is absent",
    "IM": "has reduced {gene} enzyme activity — drug metabolism may be slower than normal",
    "NM": "has normal {gene} enzyme activity — standard drug metabolism expected",
    "RM": "has increased {gene} enzyme activity — may metabolize drugs faster than normal",
    "UM": "has greatly increased {gene} enzyme activity — rapid drug metabolism may reduce efficacy or increase toxicity",
}


def _build_gene_panel(results):
    """
    Build a de-duplicated gene panel from per-drug pipeline results.
    Returns one entry per unique gene with variant details.
    """
    seen = {}
    for r in results:
        pgx = r.get("pharmacogenomic_profile", {})
        gene = pgx.get("primary_gene", "")
        if not gene or gene in seen:
            continue

        phenotype = pgx.get("phenotype", "Unknown")
        pheno_key = phenotype if phenotype in _PHENOTYPE_SUMMARIES else "NM"
        summary = f"This patient {_PHENOTYPE_SUMMARIES[pheno_key].format(gene=gene)}"

        variants = pgx.get("detected_variants", [])

        seen[gene] = {
            "gene": gene,
            "diplotype": pgx.get("diplotype", "Unknown"),
            "phenotype": phenotype,
            "genetic_phenotype": pgx.get("genetic_phenotype", phenotype),
            "active_inhibitor": pgx.get("active_inhibitor"),
            "variant_count": len(variants),
            "summary": summary,
            "variants": variants,
        }

    return list(seen.values())
