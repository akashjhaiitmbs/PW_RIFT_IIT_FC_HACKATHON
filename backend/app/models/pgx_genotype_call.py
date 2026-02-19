import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class PGxGenotypeCall(Base):
    __tablename__ = "pgx_genotype_calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vcf_upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vcf_uploads.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    gene: Mapped[str] = mapped_column(String(20), nullable=False)
    diplotype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phenotype: Mapped[str | None] = mapped_column(String(30), nullable=True)
    genetic_activity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    copy_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_structural_variant: Mapped[bool] = mapped_column(Boolean, default=False)
    calling_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    raw_pypgx_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
