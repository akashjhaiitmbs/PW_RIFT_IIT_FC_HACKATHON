"""
Phenoconversion engine — adjusts genetic activity score based on
co-administered inhibitors/inducers from the registry table.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inhibitor_registry import InhibitorInducerRegistry
from app.services.activity_score import genetic_score_to_phenotype


@dataclass
class PhenoconversionResult:
    clinical_activity_score: float
    clinical_phenotype: str
    phenoconversion_occurred: bool
    active_inhibitor: Optional[str]
    inhibition_factor: float


async def apply_phenoconversion(
    gene: str,
    genetic_activity_score: float,
    concurrent_medications: List[str],
    db: AsyncSession,
) -> PhenoconversionResult:
    """
    Steps:
      1. Query inhibitor_inducer_registry for each medication × gene.
      2. Find the most potent interaction (minimum inhibition_factor for
         inhibitors, maximum for inducers — but we take the value that
         deviates most from 1.0).
      3. clinical_activity_score = genetic_activity_score × chosen_factor
      4. Re-map to phenotype label.
    """
    # No co-medications → identity
    if not concurrent_medications:
        return _no_change(gene, genetic_activity_score)

    upper_meds = [m.upper() for m in concurrent_medications]

    stmt = select(InhibitorInducerRegistry).where(
        InhibitorInducerRegistry.gene == gene,
        InhibitorInducerRegistry.drug_name.in_(upper_meds),
    )
    rows = (await db.execute(stmt)).scalars().all()

    if not rows:
        return _no_change(gene, genetic_activity_score)

    # Pick factor that deviates most from 1.0
    best_row: Optional[InhibitorInducerRegistry] = None
    best_deviation = 0.0
    for row in rows:
        deviation = abs(row.inhibition_factor - 1.0)
        if deviation > best_deviation:
            best_deviation = deviation
            best_row = row

    if best_row is None:
        return _no_change(gene, genetic_activity_score)

    factor = best_row.inhibition_factor
    clinical_score = round(genetic_activity_score * factor, 4)
    clinical_phenotype = genetic_score_to_phenotype(gene, clinical_score)
    genetic_phenotype = genetic_score_to_phenotype(gene, genetic_activity_score)
    converted = clinical_phenotype != genetic_phenotype

    return PhenoconversionResult(
        clinical_activity_score=clinical_score,
        clinical_phenotype=clinical_phenotype,
        phenoconversion_occurred=converted,
        active_inhibitor=best_row.drug_name if converted else None,
        inhibition_factor=factor,
    )


def _no_change(gene: str, score: float) -> PhenoconversionResult:
    pheno = genetic_score_to_phenotype(gene, score)
    return PhenoconversionResult(
        clinical_activity_score=score,
        clinical_phenotype=pheno,
        phenoconversion_occurred=False,
        active_inhibitor=None,
        inhibition_factor=1.0,
    )
