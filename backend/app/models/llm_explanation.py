import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class LLMExplanation(Base):
    __tablename__ = "llm_explanations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    risk_analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_analyses.id"), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    mechanism_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    guideline_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    phenoconversion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_context_chunks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
