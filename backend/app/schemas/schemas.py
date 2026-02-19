"""Pydantic request/response schemas for all API endpoints."""
from __future__ import annotations
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
import uuid

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Standard envelope
# ---------------------------------------------------------------------------
class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    vcf_upload_id: uuid.UUID
    patient_id: uuid.UUID
    patient_code: str
    parsing_status: str
    total_variants_found: int
    genes_detected: List[str]


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    vcf_upload_id: uuid.UUID
    drugs: List[str] = Field(..., description="List of drug names e.g. ['CODEINE', 'WARFARIN']")
    concurrent_medications: List[str] = Field(
        default_factory=list,
        description="Co-administered drugs for phenoconversion check",
    )


# ---------------------------------------------------------------------------
# Results — hackathon schema
# ---------------------------------------------------------------------------
class RiskAssessmentSchema(BaseModel):
    risk_label: Optional[str]
    confidence_score: Optional[float]
    severity: Optional[str]


class DetectedVariantSchema(BaseModel):
    rsid: Optional[str]
    gene: Optional[str]
    position: Optional[int]
    ref: Optional[str]
    alt: Optional[str]
    genotype: Optional[str]
    star_allele: Optional[str]
    filter: Optional[str]


class PharmacogenomicProfileSchema(BaseModel):
    primary_gene: Optional[str]
    diplotype: Optional[str]
    phenotype: Optional[str]
    detected_variants: List[DetectedVariantSchema] = []


class ClinicalRecommendationSchema(BaseModel):
    action: Optional[str]
    alternative_drugs: List[str] = []
    cpic_guideline_version: Optional[str]
    evidence_level: Optional[str]
    phenoconversion_note: Optional[str]


class LLMExplanationSchema(BaseModel):
    summary: Optional[str]
    mechanism: Optional[str]
    guideline_recommendation: Optional[str]
    phenoconversion_explanation: Optional[str]


class QualityMetricsSchema(BaseModel):
    vcf_parsing_success: bool
    variants_detected: int
    genes_called_successfully: List[str] = []
    genes_failed: List[str] = []
    confidence_score: Optional[float]
    phenoconversion_detected: bool


class DrugResultSchema(BaseModel):
    patient_id: str
    drug: str
    timestamp: str
    risk_assessment: RiskAssessmentSchema
    pharmacogenomic_profile: PharmacogenomicProfileSchema
    clinical_recommendation: ClinicalRecommendationSchema
    llm_generated_explanation: LLMExplanationSchema
    quality_metrics: QualityMetricsSchema


# ---------------------------------------------------------------------------
# Supported drugs
# ---------------------------------------------------------------------------
class SupportedDrugSchema(BaseModel):
    drug: str
    primary_gene: str
