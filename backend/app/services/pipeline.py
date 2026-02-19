"""
Synchronous full-analysis pipeline — no Celery/Redis.

Called directly from POST /api/v1/analyze.
Returns the complete structured result.

Pipeline order (LLM is called LAST, never influences risk logic):
  1. Load detected_variants
  2. Run PGxCaller
  3. Save pgx_genotype_calls
  4. For each drug:
       a. Determine primary gene(s)
       b. Calculate genetic_activity_score
       c. Apply phenoconversion
       d. CPIC lookup
       e. Special cases (AZATHIOPRINE worst-of-two, WARFARIN VKORC1)
       f. Calculate confidence
       g. Save risk_analyses row
  5. Call LLM once per drug, save llm_explanations
  6. Return assembled result dicts
"""
from __future__ import annotations
import uuid
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.detected_variant import DetectedVariant
from app.models.pgx_genotype_call import PGxGenotypeCall
from app.models.risk_analysis import RiskAnalysis
from app.models.llm_explanation import LLMExplanation
from app.models.analysis_request import AnalysisRequest
from app.models.vcf_upload import VCFUpload
from app.models.patient import Patient

from app.services.pgx_caller import PGxCaller
from app.services.activity_score import calculate_genetic_activity_score, genetic_score_to_phenotype
from app.services.phenoconversion import apply_phenoconversion
from app.services.cpic_engine import lookup_cpic, DRUG_TO_GENE
from app.services.confidence import calculate_confidence
from app.services.llm_service import LLMExplainer

# ── phenotype severity ordering (worst = lowest index) ──────────────────────
_PHENOTYPE_SEVERITY = {"PM": 0, "IM": 1, "NM": 2, "RM": 3, "UM": 4, "Unknown": 5}


def _worse_phenotype(a: str, b: str) -> str:
    """Return the phenotype with lower activity (more severe)."""
    return a if _PHENOTYPE_SEVERITY.get(a, 5) <= _PHENOTYPE_SEVERITY.get(b, 5) else b


# ── VKORC1 check ──────────────────────────────────────────────────────────
async def _vkorc1_note(patient_id: uuid.UUID, vcf_upload_id: uuid.UUID, db: AsyncSession) -> str:
    stmt = select(DetectedVariant).where(
        DetectedVariant.patient_id == patient_id,
        DetectedVariant.vcf_upload_id == vcf_upload_id,
        DetectedVariant.rsid == "rs9923231",
    )
    row = (await db.execute(stmt)).scalars().first()
    if not row:
        return ""
    gt = row.genotype or ""
    if gt == "1/1":
        return " VKORC1 rs9923231: AA genotype (High Sensitivity) — consider starting dose 0.5-2 mg/day."
    if gt == "0/1":
        return " VKORC1 rs9923231: GA genotype (Intermediate Sensitivity)."
    if gt == "0/0":
        return " VKORC1 rs9923231: GG genotype (Low Sensitivity) — standard or higher dose may be needed."
    return ""


# ── main pipeline ──────────────────────────────────────────────────────────
async def run_analysis_pipeline(
    analysis_request_id: uuid.UUID,
    db: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    Runs the complete PGx risk pipeline synchronously.
    Updates AnalysisRequest.status throughout.
    Returns a list of result dicts (one per drug).
    """
    now = datetime.now(timezone.utc)

    # ── load request ─────────────────────────────────────────────────────
    req: Optional[AnalysisRequest] = (
        await db.get(AnalysisRequest, analysis_request_id)
    )
    if not req:
        raise ValueError(f"AnalysisRequest {analysis_request_id} not found")

    req.status = "processing"
    await db.commit()

    try:
        result = await _pipeline(req, db)
        req.status = "complete"
        req.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return result
    except Exception as exc:
        req.status = "failed"
        req.error_message = str(exc)
        await db.commit()
        raise


async def _pipeline(req: AnalysisRequest, db: AsyncSession) -> List[Dict[str, Any]]:
    patient_id = req.patient_id
    vcf_upload_id = req.vcf_upload_id
    drugs: List[str] = req.requested_drugs or []
    concurrent_meds: List[str] = req.concurrent_medications or []

    # ── 1. Load VCF upload & patient ─────────────────────────────────────
    vcf_upload: VCFUpload = await db.get(VCFUpload, vcf_upload_id)
    patient: Patient = await db.get(Patient, patient_id)

    # ── 2. Load detected variants ────────────────────────────────────────
    stmt = select(DetectedVariant).where(
        DetectedVariant.vcf_upload_id == vcf_upload_id
    )
    all_variants: List[DetectedVariant] = (await db.execute(stmt)).scalars().all()
    variant_dicts = [
        {
            "rsid": v.rsid,
            "gene": v.gene,
            "chromosome": v.chromosome,
            "position": v.position,
            "ref_allele": v.ref_allele,
            "alt_allele": v.alt_allele,
            "genotype": v.genotype,
            "star_allele": v.star_allele,
            "quality_score": v.quality_score,
            "filter_status": v.filter_status,
        }
        for v in all_variants
    ]

    # ── 3. Run PGxCaller ─────────────────────────────────────────────────
    caller = PGxCaller()
    pgx_results = caller.call(vcf_path=vcf_upload.file_path)

    # Save pgx_genotype_calls
    gene_call_map: Dict[str, PGxGenotypeCall] = {}
    for gene, gdata in pgx_results.items():
        diplotype = gdata.get("diplotype") or "Unknown"
        gen_score = calculate_genetic_activity_score(gene, diplotype)
        pheno = gdata.get("phenotype") or "Unknown"
        if pheno == "Unknown" and gen_score is not None:
            pheno = genetic_score_to_phenotype(gene, gen_score)

        call = PGxGenotypeCall(
            id=uuid.uuid4(),
            vcf_upload_id=vcf_upload_id,
            patient_id=patient_id,
            gene=gene,
            diplotype=diplotype,
            phenotype=pheno,
            genetic_activity_score=gen_score,
            copy_number=gdata.get("copy_number"),
            has_structural_variant=bool(gdata.get("has_structural_variant", False)),
            calling_method=gdata.get("calling_method") or "Unknown",
            raw_pypgx_output=gdata.get("raw_output") or {},
        )
        db.add(call)
        gene_call_map[gene] = call

    await db.commit()
    for call in gene_call_map.values():
        await db.refresh(call)

    # ── 4. Per-drug analysis ──────────────────────────────────────────────
    results = []
    explainer = LLMExplainer()

    for drug in drugs:
        drug = drug.upper()
        primary_gene = DRUG_TO_GENE.get(drug, "Unknown")
        risk_rec = await _analyze_drug(
            drug=drug,
            primary_gene=primary_gene,
            gene_call_map=gene_call_map,
            all_variants=variant_dicts,
            concurrent_meds=concurrent_meds,
            patient_id=patient_id,
            vcf_upload_id=vcf_upload_id,
            db=db,
        )
        results.append((drug, risk_rec))

    # ── 5. LLM explanations (after all deterministic logic) ───────────────
    final = []
    for drug, (risk_row, gene_call, pheno_result, cpic_result) in results:
        llm_rec = await explainer.explain_and_save(
            db=db,
            risk_analysis_id=risk_row.id,
            gene=risk_row.primary_gene or "",
            diplotype=risk_row.diplotype or "Unknown",
            genetic_phenotype=risk_row.genetic_phenotype or "Unknown",
            clinical_phenotype=risk_row.clinical_phenotype or "Unknown",
            drug_name=drug,
            risk_label=risk_row.risk_label or "Unknown",
            phenoconversion_occurred=risk_row.phenoconversion_occurred,
            active_inhibitor=risk_row.active_inhibitor,
        )

        # Build hackathon-required response schema
        gene_variants = [v for v in variant_dicts if v.get("gene") == risk_row.primary_gene]
        genes_called_ok = [g for g, c in gene_call_map.items() if (c.phenotype or "") != "Unknown"]
        genes_failed = [g for g, c in gene_call_map.items() if (c.phenotype or "") == "Unknown"]

        final.append(_build_result(
            patient=patient,
            drug=drug,
            risk_row=risk_row,
            llm_rec=llm_rec,
            gene_variants=gene_variants,
            vcf_upload=vcf_upload,
            genes_called_ok=genes_called_ok,
            genes_failed=genes_failed,
        ))

    return final


# ── drug analysis sub-routine ─────────────────────────────────────────────
async def _analyze_drug(
    drug: str,
    primary_gene: str,
    gene_call_map: Dict[str, PGxGenotypeCall],
    all_variants: List[Dict[str, Any]],
    concurrent_meds: List[str],
    patient_id: uuid.UUID,
    vcf_upload_id: uuid.UUID,
    db: AsyncSession,
):
    now = datetime.now(timezone.utc)

    # Determine gene(s) to use
    if drug == "AZATHIOPRINE":
        tpmt_call = gene_call_map.get("TPMT")
        nudt_call = gene_call_map.get("NUDT15")
        tpmt_pheno = getattr(tpmt_call, "phenotype", "Unknown") or "Unknown"
        nudt_pheno = getattr(nudt_call, "phenotype", "Unknown") or "Unknown"
        # Take the worse phenotype
        worst = _worse_phenotype(tpmt_pheno, nudt_pheno)
        gene_call = tpmt_call if worst == tpmt_pheno else nudt_call
        primary_gene = "TPMT+NUDT15"
    else:
        gene_call = gene_call_map.get(primary_gene)

    diplotype = getattr(gene_call, "diplotype", "Unknown") or "Unknown"
    gen_score = getattr(gene_call, "genetic_activity_score", None)
    if gen_score is None:
        gen_score = calculate_genetic_activity_score(primary_gene.split("+")[0], diplotype) or 0.0

    # Phenoconversion
    pheno_result = await apply_phenoconversion(
        gene=primary_gene.split("+")[0],
        genetic_activity_score=gen_score,
        concurrent_medications=concurrent_meds,
        db=db,
    )

    genetic_phenotype = genetic_score_to_phenotype(primary_gene.split("+")[0], gen_score)

    # CPIC lookup
    cpic_result = lookup_cpic(drug, pheno_result.clinical_phenotype)
    dosing = cpic_result["dosing"]

    # WARFARIN VKORC1 special case
    if drug == "WARFARIN":
        vkorc1_note = await _vkorc1_note(patient_id, vcf_upload_id, db)
        if vkorc1_note:
            dosing += vkorc1_note

    # Confidence score
    gene_variants = [v for v in all_variants if v.get("gene") == primary_gene.split("+")[0]]
    call_dict = {
        "calling_method": getattr(gene_call, "calling_method", "Unknown"),
        "phenotype": getattr(gene_call, "phenotype", "Unknown"),
        "has_structural_variant": getattr(gene_call, "has_structural_variant", False),
        "error": None,
    }
    conf = calculate_confidence(call_dict, gene_variants, cpic_result, pheno_result.phenoconversion_occurred)

    # Save risk_analyses row
    risk_row = RiskAnalysis(
        id=uuid.uuid4(),
        patient_id=patient_id,
        vcf_upload_id=vcf_upload_id,
        drug_name=drug,
        primary_gene=primary_gene,
        diplotype=diplotype,
        genetic_phenotype=genetic_phenotype,
        active_inhibitor=pheno_result.active_inhibitor,
        inhibition_factor=pheno_result.inhibition_factor,
        genetic_activity_score=gen_score,
        clinical_activity_score=pheno_result.clinical_activity_score,
        clinical_phenotype=pheno_result.clinical_phenotype,
        phenoconversion_occurred=pheno_result.phenoconversion_occurred,
        risk_label=cpic_result["risk_label"],
        severity=cpic_result["severity"],
        confidence_score=conf,
        dosing_recommendation=dosing,
        alternative_drugs=cpic_result.get("alternatives") or [],
        cpic_guideline_version=cpic_result.get("cpic_version"),
        cpic_evidence_level=cpic_result.get("evidence_level"),
        created_at=now,
        updated_at=now,
    )
    db.add(risk_row)
    await db.commit()
    await db.refresh(risk_row)

    return risk_row, gene_call, pheno_result, cpic_result


# ── response builder ──────────────────────────────────────────────────────
def _build_result(
    patient: Patient,
    drug: str,
    risk_row: RiskAnalysis,
    llm_rec: LLMExplanation,
    gene_variants: List[Dict[str, Any]],
    vcf_upload: VCFUpload,
    genes_called_ok: List[str],
    genes_failed: List[str],
) -> Dict[str, Any]:
    phenoconv_note = (
        f"Patient is genotypically {risk_row.genetic_phenotype} but phenotypically "
        f"{risk_row.clinical_phenotype} due to {risk_row.active_inhibitor}."
        if risk_row.phenoconversion_occurred
        else "No phenoconversion detected."
    )

    return {
        "patient_id": patient.patient_code,
        "drug": drug,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "risk_assessment": {
            "risk_label": risk_row.risk_label,
            "confidence_score": risk_row.confidence_score,
            "severity": risk_row.severity,
        },
        "pharmacogenomic_profile": {
            "primary_gene": risk_row.primary_gene,
            "diplotype": risk_row.diplotype,
            "phenotype": risk_row.clinical_phenotype,
            "detected_variants": [
                {
                    "rsid": v.get("rsid"),
                    "gene": v.get("gene"),
                    "position": v.get("position"),
                    "ref": v.get("ref_allele"),
                    "alt": v.get("alt_allele"),
                    "genotype": v.get("genotype"),
                    "star_allele": v.get("star_allele"),
                    "filter": v.get("filter_status"),
                }
                for v in gene_variants
            ],
        },
        "clinical_recommendation": {
            "action": risk_row.dosing_recommendation,
            "alternative_drugs": risk_row.alternative_drugs or [],
            "cpic_guideline_version": risk_row.cpic_guideline_version,
            "evidence_level": risk_row.cpic_evidence_level,
            "phenoconversion_note": phenoconv_note,
        },
        "llm_generated_explanation": {
            "summary": llm_rec.summary if llm_rec else "",
            "mechanism": llm_rec.mechanism_explanation if llm_rec else "",
            "guideline_recommendation": llm_rec.guideline_quote if llm_rec else "",
            "phenoconversion_explanation": llm_rec.phenoconversion_note if llm_rec else "",
        },
        "quality_metrics": {
            "vcf_parsing_success": vcf_upload.parsing_status == "success",
            "variants_detected": vcf_upload.total_variants_found or 0,
            "genes_called_successfully": genes_called_ok,
            "genes_failed": genes_failed,
            "confidence_score": risk_row.confidence_score,
            "phenoconversion_detected": risk_row.phenoconversion_occurred,
        },
    }
