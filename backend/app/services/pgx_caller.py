"""
PyPGx wrapper — calls the Stargazer algorithm for 7 pharmacogenes.

If PyPGx is not installed or a gene fails, returns a safe error dict
so the rest of the pipeline can continue.
"""
from __future__ import annotations
import os
import tempfile
from typing import Dict, Any

SUPPORTED_GENES = [
    "CYP2D6",
    "CYP2C19",
    "CYP2C9",
    "SLCO1B1",
    "TPMT",
    "NUDT15",
    "DPYD",
]


class PGxCaller:
    """
    Wraps PyPGx to produce diplotype/phenotype calls per gene.

    Usage::
        caller = PGxCaller()
        results = caller.call(vcf_path="/path/to/sample.vcf", output_dir="/tmp/pgx_out")
        # results["CYP2D6"] → {"diplotype": "*1/*4", "phenotype": "IM", ...}
    """

    def call(self, vcf_path: str, output_dir: str | None = None) -> Dict[str, Any]:
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="pgx_")

        results: Dict[str, Any] = {}
        for gene in SUPPORTED_GENES:
            results[gene] = self._call_gene(gene, vcf_path, output_dir)
        return results

    # ------------------------------------------------------------------
    def _call_gene(self, gene: str, vcf_path: str, output_dir: str) -> Dict[str, Any]:
        gene_out = os.path.join(output_dir, gene)
        os.makedirs(gene_out, exist_ok=True)
        try:
            import pypgx.api as pgx_api  # type: ignore

            result = pgx_api.run_ngs_pipeline(
                input_path=vcf_path,
                gene=gene,
                output_dir=gene_out,
            )
            return self._parse_result(gene, result)
        except ImportError:
            # PyPGx not installed — return mock/unknown
            return self._unknown_result(gene, "PyPGx not installed")
        except Exception as exc:
            return self._unknown_result(gene, str(exc))

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_result(gene: str, raw: Any) -> Dict[str, Any]:
        """
        Convert PyPGx output to our standard dict.
        PyPGx returns a ArchiveFile or similar; we attempt common attribute access.
        """
        try:
            # PyPGx result is usually a pandas-like object or dict
            if hasattr(raw, "to_dict"):
                data = raw.to_dict()
            elif isinstance(raw, dict):
                data = raw
            else:
                data = {}

            diplotype = data.get("diplotype", data.get("Diplotype", "Unknown"))
            phenotype = data.get("phenotype", data.get("Phenotype", "Unknown"))
            copy_number = data.get("copy_number", data.get("CopyNumber"))

            # Structural variant detection for CYP2D6
            has_sv = False
            if gene == "CYP2D6" and copy_number is not None:
                try:
                    cn = int(copy_number)
                    has_sv = cn < 2 or cn > 2
                except (ValueError, TypeError):
                    pass

            return {
                "diplotype": str(diplotype) if diplotype else "Unknown",
                "phenotype": str(phenotype) if phenotype else "Unknown",
                "copy_number": int(copy_number) if copy_number is not None else None,
                "has_structural_variant": has_sv,
                "calling_method": "PyPGx-Stargazer",
                "raw_output": data,
                "error": None,
            }
        except Exception as exc:
            return PGxCaller._unknown_result(gene, f"Parse error: {exc}")

    @staticmethod
    def _unknown_result(gene: str, reason: str) -> Dict[str, Any]:
        return {
            "diplotype": "Unknown",
            "phenotype": "Unknown",
            "copy_number": None,
            "has_structural_variant": False,
            "calling_method": "Unknown",
            "raw_output": {},
            "error": reason,
        }
