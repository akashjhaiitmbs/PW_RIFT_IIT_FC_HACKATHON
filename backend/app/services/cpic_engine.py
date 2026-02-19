"""
CPIC lookup engine — deterministic drug × phenotype → risk result.
This table is the authoritative source of risk_label, severity,
dosing_recommendation, and alternative_drugs.

The LLM NEVER modifies these values.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Decision table
# ---------------------------------------------------------------------------
CPIC_TABLE: Dict[Tuple[str, str], Dict[str, Any]] = {
    # ── CODEINE (primary gene: CYP2D6) ──────────────────────────────────
    ("CODEINE", "PM"): {
        "risk_label": "Ineffective",
        "severity": "high",
        "dosing": "Avoid codeine. Use non-opioid analgesic or morphine with dose titration.",
        "alternatives": ["MORPHINE", "ACETAMINOPHEN"],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("CODEINE", "IM"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "dosing": "Use lowest effective dose. Monitor closely for reduced efficacy.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("CODEINE", "NM"): {
        "risk_label": "Safe",
        "severity": "none",
        "dosing": "Initiate standard dosing per label.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("CODEINE", "UM"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "dosing": "Avoid codeine. Risk of life-threatening morphine toxicity.",
        "alternatives": ["MORPHINE"],
        "cpic_version": "2022",
        "evidence_level": "A",
    },

    # ── WARFARIN (primary gene: CYP2C9; VKORC1 appended separately) ─────
    ("WARFARIN", "PM"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "dosing": "Reduce warfarin dose by 25-50%. Target INR 2.0-3.0. Monitor INR frequently.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("WARFARIN", "IM"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "dosing": "Consider 10-25% dose reduction. Monitor INR closely.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("WARFARIN", "NM"): {
        "risk_label": "Safe",
        "severity": "none",
        "dosing": "Initiate standard dosing. Monitor INR per protocol.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },

    # ── CLOPIDOGREL (primary gene: CYP2C19) ─────────────────────────────
    ("CLOPIDOGREL", "PM"): {
        "risk_label": "Ineffective",
        "severity": "critical",
        "dosing": "Avoid clopidogrel. Use prasugrel or ticagrelor.",
        "alternatives": ["PRASUGREL", "TICAGRELOR"],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("CLOPIDOGREL", "IM"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "dosing": "Use with caution. Consider alternative antiplatelet agent.",
        "alternatives": ["TICAGRELOR"],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("CLOPIDOGREL", "NM"): {
        "risk_label": "Safe",
        "severity": "none",
        "dosing": "Initiate standard dose.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("CLOPIDOGREL", "UM"): {
        "risk_label": "Safe",
        "severity": "low",
        "dosing": "Standard dosing. May have enhanced response.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "B",
    },

    # ── SIMVASTATIN (primary gene: SLCO1B1) ──────────────────────────────
    ("SIMVASTATIN", "Normal Function"): {
        "risk_label": "Safe",
        "severity": "none",
        "dosing": "Standard dosing.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("SIMVASTATIN", "Decreased Function"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "dosing": "Limit simvastatin dose to 20mg/day or switch to rosuvastatin/pravastatin.",
        "alternatives": ["ROSUVASTATIN", "PRAVASTATIN"],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("SIMVASTATIN", "Poor Function"): {
        "risk_label": "Toxic",
        "severity": "high",
        "dosing": "Avoid simvastatin. High risk of myopathy/rhabdomyolysis. Use rosuvastatin or pravastatin.",
        "alternatives": ["ROSUVASTATIN", "PRAVASTATIN"],
        "cpic_version": "2022",
        "evidence_level": "A",
    },

    # ── AZATHIOPRINE (primary genes: TPMT + NUDT15 — worst wins) ─────────
    ("AZATHIOPRINE", "PM"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "dosing": "Reduce dose by 90% or avoid. Fatal myelosuppression risk.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("AZATHIOPRINE", "IM"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "dosing": "Reduce dose by 30-70%. Monitor CBC weekly.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("AZATHIOPRINE", "NM"): {
        "risk_label": "Safe",
        "severity": "none",
        "dosing": "Standard dosing. Monitor CBC per protocol.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },

    # ── FLUOROURACIL / 5-FU (primary gene: DPYD) ─────────────────────────
    ("FLUOROURACIL", "PM"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "dosing": "Avoid 5-FU/capecitabine. Life-threatening toxicity risk.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("FLUOROURACIL", "IM"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "dosing": "Reduce starting dose by 50%. Titrate based on toxicity and response.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
    ("FLUOROURACIL", "NM"): {
        "risk_label": "Safe",
        "severity": "none",
        "dosing": "Standard dosing per oncology protocol.",
        "alternatives": [],
        "cpic_version": "2022",
        "evidence_level": "A",
    },
}

_FALLBACK: Dict[str, Any] = {
    "risk_label": "Unknown",
    "severity": "none",
    "dosing": "Insufficient data for this drug-gene combination.",
    "alternatives": [],
    "cpic_version": None,
    "evidence_level": None,
}

# ---------------------------------------------------------------------------
# Drug → primary gene mapping
# ---------------------------------------------------------------------------
DRUG_TO_GENE: Dict[str, str] = {
    "CODEINE":      "CYP2D6",
    "WARFARIN":     "CYP2C9",
    "CLOPIDOGREL":  "CYP2C19",
    "SIMVASTATIN":  "SLCO1B1",
    "AZATHIOPRINE": "TPMT",   # also checks NUDT15
    "FLUOROURACIL": "DPYD",
}

SUPPORTED_DRUGS = list(DRUG_TO_GENE.keys())


def lookup_cpic(drug: str, clinical_phenotype: str) -> Dict[str, Any]:
    """Return the CPIC decision dict for a (drug, phenotype) pair."""
    key = (drug.upper(), clinical_phenotype)
    return dict(CPIC_TABLE.get(key, _FALLBACK))
