"""VCF file parser — no external dependencies, pure Python."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class VCFParseResult:
    success: bool
    variants: List[Dict[str, Any]] = field(default_factory=list)
    vcf_version: str | None = None
    total_variants: int = 0
    error: str | None = None


class VCFParser:
    """
    Parses a VCF 4.x file and returns structured variant records.

    Validation rules:
      - File must start with ##fileformat=VCFv4
      - Must have at least one data row
      - At least one row must have a GENE= tag in INFO
    """

    def parse(self, file_path: str) -> VCFParseResult:
        try:
            return self._parse(file_path)
        except Exception as exc:
            return VCFParseResult(success=False, error=f"Unexpected parser error: {exc}")

    # ------------------------------------------------------------------
    def _parse(self, file_path: str) -> VCFParseResult:
        vcf_version: str | None = None
        header_cols: List[str] = []
        variants: List[Dict[str, Any]] = []
        at_least_one_gene_tag = False

        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                line = raw_line.rstrip("\n\r")

                # ── meta lines ──────────────────────────────────────────
                if line.startswith("##"):
                    if line.startswith("##fileformat="):
                        vcf_version = line.split("=", 1)[1].strip()
                    continue

                # ── column header line ───────────────────────────────────
                if line.startswith("#CHROM"):
                    header_cols = line.lstrip("#").split("\t")
                    continue

                # ── data lines ───────────────────────────────────────────
                if not header_cols:
                    continue  # no header yet — skip

                parts = line.split("\t")
                if len(parts) < 8:
                    continue

                row = dict(zip(header_cols, parts))
                info_str = row.get("INFO", "")
                info = self._parse_info(info_str)

                gene = info.get("GENE")
                star = info.get("STAR")

                if gene:
                    at_least_one_gene_tag = True

                # Extract FORMAT/SAMPLE genotype
                genotype = None
                format_keys = row.get("FORMAT", "").split(":")
                sample_key = None
                for k in header_cols[9:]:  # first sample column
                    sample_key = k
                    break
                if sample_key and sample_key in row:
                    sample_vals = row[sample_key].split(":")
                    sample_map = dict(zip(format_keys, sample_vals))
                    genotype = sample_map.get("GT")

                # QUAL
                qual_raw = row.get("QUAL", ".")
                quality_score = None
                try:
                    quality_score = float(qual_raw) if qual_raw != "." else None
                except ValueError:
                    pass

                variants.append(
                    {
                        "rsid": row.get("ID", ".").strip() or None,
                        "chromosome": row.get("CHROM", "").lstrip("chr"),
                        "position": self._safe_int(row.get("POS")),
                        "ref_allele": row.get("REF", ""),
                        "alt_allele": row.get("ALT", ""),
                        "quality_score": quality_score,
                        "filter_status": row.get("FILTER", ".") or ".",
                        "gene": gene,
                        "star_allele": star,
                        "genotype": genotype,
                    }
                )

        # ── validation ───────────────────────────────────────────────────
        if vcf_version is None or "VCFv4" not in (vcf_version or ""):
            return VCFParseResult(
                success=False,
                error="Invalid VCF: file must start with ##fileformat=VCFv4",
            )
        if not variants:
            return VCFParseResult(
                success=False,
                error="Invalid VCF: no variant data rows found",
            )
        if not at_least_one_gene_tag:
            return VCFParseResult(
                success=False,
                error="Invalid VCF: no GENE= tag found in INFO column — cannot determine pharmacogene",
            )

        return VCFParseResult(
            success=True,
            variants=variants,
            vcf_version=vcf_version,
            total_variants=len(variants),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_info(info_str: str) -> Dict[str, str]:
        """Parse semicolon-delimited KEY=VALUE pairs from INFO field."""
        result: Dict[str, str] = {}
        for token in info_str.split(";"):
            if "=" in token:
                k, _, v = token.partition("=")
                result[k.strip()] = v.strip()
            else:
                result[token.strip()] = "true"
        return result

    @staticmethod
    def _safe_int(val: str | None) -> int | None:
        try:
            return int(val) if val else None
        except (ValueError, TypeError):
            return None
