import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class InhibitorInducerRegistry(Base):
    __tablename__ = "inhibitor_inducer_registry"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    drug_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gene: Mapped[str] = mapped_column(String(20), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # inhibitor | inducer
    strength: Mapped[str] = mapped_column(String(20), nullable=False)          # strong | moderate | weak
    inhibition_factor: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
