"""
Activity score calculator — star allele → numeric activity → phenotype label.
All mappings are deterministic and hardcoded per CPIC guidelines.
"""
from __future__ import annotations
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Star allele → activity value
# ---------------------------------------------------------------------------
_CYP2D6_ALLELE_VALUES: Dict[str, float] = {
    "*1": 1.0, "*2": 1.0, "*3": 0.0, "*4": 0.0, "*5": 0.0,
    "*6": 0.0, "*9": 0.5, "*10": 0.25, "*17": 0.5, "*29": 0.5, "*41": 0.5,
}

_CYP2C19_ALLELE_VALUES: Dict[str, float] = {
    "*1": 1.0, "*2": 0.0, "*3": 0.0, "*17": 1.5,
}

_CYP2C9_ALLELE_VALUES: Dict[str, float] = {
    "*1": 1.0, "*2": 0.5, "*3": 0.0,
}

# TPMT / NUDT15 — non-functional = 0, functional = 1
_TPMT_ALLELE_VALUES: Dict[str, float] = {
    "*1": 1.0, "*2": 0.0, "*3A": 0.0, "*3C": 0.0,
}

_NUDT15_ALLELE_VALUES: Dict[str, float] = {
    "*1": 1.0, "*2": 0.0, "*3": 0.0,
}

_DPYD_ALLELE_VALUES: Dict[str, float] = {
    "*1": 1.0, "*2A": 0.0, "HapB3": 0.5,
}

_SLCO1B1_ALLELE_VALUES: Dict[str, float] = {
    "*1": 1.0, "*5": 0.0,  # *5 = c.521T>C decreased function
}

_GENE_MAP: Dict[str, Dict[str, float]] = {
    "CYP2D6":  _CYP2D6_ALLELE_VALUES,
    "CYP2C19": _CYP2C19_ALLELE_VALUES,
    "CYP2C9":  _CYP2C9_ALLELE_VALUES,
    "TPMT":    _TPMT_ALLELE_VALUES,
    "NUDT15":  _NUDT15_ALLELE_VALUES,
    "DPYD":    _DPYD_ALLELE_VALUES,
    "SLCO1B1": _SLCO1B1_ALLELE_VALUES,
}

# ---------------------------------------------------------------------------
# Phenotype thresholds
# ---------------------------------------------------------------------------
def genetic_score_to_phenotype(gene: str, score: float) -> str:
    """Map a numeric activity score to a phenotype label."""
    if gene == "CYP2D6":
        if score == 0:        return "PM"
        if score < 1.25:      return "IM"
        if score <= 2.25:     return "NM"
        return "UM"

    if gene == "CYP2C19":
        if score == 0:        return "PM"
        if score < 1.25:      return "IM"
        if score <= 2.0:      return "NM"
        return "UM"

    if gene == "CYP2C9":
        if score == 0:        return "PM"
        if score < 1.5:       return "IM"
        return "NM"

    if gene in ("TPMT", "NUDT15"):
        if score == 0:        return "PM"
        if score < 2.0:       return "IM"
        return "NM"

    if gene == "DPYD":
        if score == 0:        return "PM"
        if score < 1.0:       return "IM"
        return "NM"

    if gene == "SLCO1B1":
        if score <= 0.0:      return "Poor Function"
        if score < 1.0:       return "Decreased Function"
        return "Normal Function"

    return "Unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def calculate_genetic_activity_score(gene: str, diplotype: str) -> Optional[float]:
    """
    Split diplotype on "/" and sum allele activity values.

    Handles CYP2D6 xN duplications: *1x3 means *1 × 3 copies.
    Returns None if the gene or diplotype is unrecognised.
    """
    if not diplotype or diplotype in ("Unknown", ""):
        return None

    allele_map = _GENE_MAP.get(gene)
    if allele_map is None:
        return None

    alleles = diplotype.split("/")
    total = 0.0
    for allele in alleles:
        allele = allele.strip()
        # Handle duplication notation e.g. *1x3 or *2xN
        copy_mult = 1
        if "x" in allele.lower() and gene == "CYP2D6":
            base, _, cnt = allele.lower().partition("x")
            allele = base.upper() if not base.startswith("*") else base
            # Normalise: *1x3 → base="*1", cnt="3"
            allele = allele if allele.startswith("*") else f"*{allele.lstrip('*')}"
            try:
                copy_mult = int(cnt)
            except ValueError:
                copy_mult = 1

        val = allele_map.get(allele, None)
        if val is None:
            # Unknown allele — try looking up with just the star number
            val = allele_map.get(allele.upper(), 0.0)
        total += val * copy_mult

    return round(total, 4)
