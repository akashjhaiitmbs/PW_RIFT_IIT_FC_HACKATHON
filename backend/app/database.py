from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables and seed static data."""
    from app.models import patient, vcf_upload, detected_variant  # noqa
    from app.models import pgx_genotype_call, inhibitor_registry  # noqa
    from app.models import risk_analysis, llm_explanation, analysis_request  # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_inhibitor_registry()


async def seed_inhibitor_registry():
    """Seed the inhibitor/inducer registry if empty."""
    from app.models.inhibitor_registry import InhibitorInducerRegistry
    from sqlalchemy import select
    import uuid
    from datetime import datetime, timezone

    SEED_DATA = [
        ("PAROXETINE",  "CYP2D6",  "inhibitor", "strong",   0.0,  "FDA"),
        ("FLUOXETINE",  "CYP2D6",  "inhibitor", "strong",   0.0,  "FDA"),
        ("BUPROPION",   "CYP2D6",  "inhibitor", "strong",   0.0,  "FDA"),
        ("DULOXETINE",  "CYP2D6",  "inhibitor", "moderate", 0.5,  "CPIC"),
        ("TERBINAFINE", "CYP2D6",  "inhibitor", "strong",   0.0,  "FDA"),
        ("OMEPRAZOLE",  "CYP2C19", "inhibitor", "moderate", 0.5,  "CPIC"),
        ("FLUVOXAMINE", "CYP2C19", "inhibitor", "strong",   0.0,  "FDA"),
        ("RIFAMPIN",    "CYP2C19", "inducer",   "strong",   2.0,  "FDA"),
        ("FLUCONAZOLE", "CYP2C9",  "inhibitor", "strong",   0.0,  "FDA"),
        ("AMIODARONE",  "CYP2C9",  "inhibitor", "moderate", 0.5,  "FDA"),
        ("RIFAMPIN",    "CYP2C9",  "inducer",   "strong",   2.0,  "FDA"),
    ]

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(InhibitorInducerRegistry).limit(1))
        if result.scalars().first() is not None:
            return  # already seeded

        now = datetime.now(timezone.utc)
        for drug, gene, itype, strength, factor, source in SEED_DATA:
            entry = InhibitorInducerRegistry(
                id=uuid.uuid4(),
                drug_name=drug,
                gene=gene,
                interaction_type=itype,
                strength=strength,
                inhibition_factor=factor,
                source=source,
                created_at=now,
            )
            session.add(entry)
        await session.commit()
