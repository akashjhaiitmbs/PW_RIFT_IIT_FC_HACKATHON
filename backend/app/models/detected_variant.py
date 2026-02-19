import uuid
from datetime import datetime, timezone
from sqlalchemy import String, BigInteger, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class DetectedVariant(Base):
    __tablename__ = "detected_variants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vcf_upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vcf_uploads.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    rsid: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gene: Mapped[str | None] = mapped_column(String(20), nullable=True)
    chromosome: Mapped[str | None] = mapped_column(String(5), nullable=True)
    position: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ref_allele: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alt_allele: Mapped[str | None] = mapped_column(String(50), nullable=True)
    genotype: Mapped[str | None] = mapped_column(String(10), nullable=True)
    star_allele: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    filter_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
