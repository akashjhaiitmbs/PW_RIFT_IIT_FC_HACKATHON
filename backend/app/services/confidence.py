"""
Confidence score calculator — purely deterministic, never set by LLM.

Starts at 1.0 and applies deductions based on data quality indicators.
"""
from __future__ import annotations
from typing import Any, Dict, List


def calculate_confidence(
    gene_call: Dict[str, Any],
    variant_data: List[Dict[str, Any]],
    cpic_result: Dict[str, Any],
    phenoconversion_occurred: bool = False,
) -> float:
    """
    Parameters
    ----------
    gene_call : dict
        Single gene result dict from PGxCaller (or from pgx_genotype_calls row).
        Expected keys: calling_method, phenotype, has_structural_variant
    variant_data : list of dicts
        Detected variants for the gene. Each dict should have 'filter_status'.
    cpic_result : dict
        Result from lookup_cpic(). Expected key: risk_label
    phenoconversion_occurred : bool

    Returns
    -------
    float clamped to [0.0, 1.0], rounded to 2 decimal places
    """
    score = 1.0

    calling_method = gene_call.get("calling_method", "") or ""
    phenotype = gene_call.get("phenotype", "") or ""
    has_sv = bool(gene_call.get("has_structural_variant", False))
    risk_label = cpic_result.get("risk_label", "") or ""

    # Bad calling method
    if calling_method in ("Unknown", "") or gene_call.get("error"):
        score -= 0.4

    # Unknown phenotype
    if phenotype == "Unknown":
        score -= 0.3

    # Structural variant (higher uncertainty in CNV calls)
    if has_sv:
        score -= 0.1

    # Any variant failed quality filter
    any_failed = any(
        (v.get("filter_status") or "PASS") not in ("PASS", ".", "")
        for v in (variant_data or [])
    )
    if any_failed:
        score -= 0.1

    # Unknown CPIC result
    if risk_label == "Unknown":
        score -= 0.2

    # Slight uncertainty added by phenoconversion
    if phenoconversion_occurred:
        score -= 0.05

    return round(max(0.0, min(1.0, score)), 2)
