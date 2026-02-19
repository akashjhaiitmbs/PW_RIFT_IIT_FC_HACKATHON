import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class RiskAnalysis(Base):
    __tablename__ = "risk_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    vcf_upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vcf_uploads.id"), nullable=False)
    drug_name: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_gene: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diplotype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    genetic_phenotype: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active_inhibitor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    inhibition_factor: Mapped[float] = mapped_column(Float, default=1.0)
    genetic_activity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    clinical_activity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    clinical_phenotype: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phenoconversion_occurred: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_label: Mapped[str | None] = mapped_column(String(30), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dosing_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternative_drugs: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    cpic_guideline_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cpic_evidence_level: Mapped[str | None] = mapped_column(String(5), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
