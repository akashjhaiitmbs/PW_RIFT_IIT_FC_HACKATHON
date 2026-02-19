/**
 * PhenoconversionPanel — Special "before/after" comparison
 * Shown when phenoconversion is detected for a drug.
 */
export default function PhenoconversionPanel({ gene, diplotype, geneticPhenotype, clinicalPhenotype, inhibitor }) {
    if (!inhibitor) return null;

    const phenoStyle = (p) => {
        const map = {
            PM: { bg: '#FEF2F2', border: '#FECACA', text: '#DC2626' },
            IM: { bg: '#FFFBEB', border: '#FDE68A', text: '#D97706' },
            NM: { bg: '#F0FDF4', border: '#BBF7D0', text: '#16A34A' },
            RM: { bg: '#EFF6FF', border: '#BFDBFE', text: '#2563EB' },
            UM: { bg: '#FEF2F2', border: '#FECACA', text: '#DC2626' },
        };
        return map[p] || { bg: '#F8FAFC', border: '#E2E8F0', text: '#64748B' };
    };

    const genStyle = phenoStyle(geneticPhenotype);
    const clinStyle = phenoStyle(clinicalPhenotype);

    return (
        <div className="phenoconv-container">
            <div className="flex items-center gap-2 mb-4">
                <span className="text-sm font-bold text-[#D97706]">⚡ Phenoconversion Detected</span>
                <span className="text-[10px] font-mono text-[#9CA3AF]">{gene}</span>
            </div>

            <div className="phenoconv-grid">
                {/* Left — Genetic Profile */}
                <div className="phenoconv-box" style={{ borderColor: genStyle.border }}>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-3">
                        Genetic Profile
                    </div>
                    <div className="text-[10px] text-[#6B7280] mb-1">from VCF</div>
                    <div className="text-lg font-mono font-black text-[#0F172A] mb-2">{diplotype}</div>
                    <span
                        className="inline-block text-xs font-bold px-3 py-1 rounded-full"
                        style={{ background: genStyle.bg, color: genStyle.text, border: `1.5px solid ${genStyle.border}` }}
                    >
                        {geneticPhenotype}
                    </span>
                    <div className="mt-3 text-[10px] text-[#9CA3AF]">↑ Your genes</div>
                </div>

                {/* Arrow */}
                <div className="phenoconv-arrow">
                    <div className="phenoconv-arrow-line" />
                    <div className="phenoconv-arrow-head">→</div>
                </div>

                {/* Right — Clinical Profile */}
                <div className="phenoconv-box phenoconv-box-clinical" style={{ borderColor: clinStyle.border }}>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-[#D97706] mb-3">
                        Clinical Profile
                    </div>
                    <div className="text-[10px] text-[#6B7280] mb-1">with current meds</div>
                    <div className="text-lg font-mono font-black text-[#0F172A] mb-2">{diplotype}</div>
                    <span
                        className="inline-block text-xs font-bold px-3 py-1 rounded-full"
                        style={{ background: clinStyle.bg, color: clinStyle.text, border: `1.5px solid ${clinStyle.border}` }}
                    >
                        {clinicalPhenotype}
                    </span>
                    <div className="mt-3 text-[10px] text-[#D97706] font-semibold">
                        ↑ + {inhibitor} <span className="text-[#9CA3AF] font-normal">(strong inhibitor)</span>
                    </div>
                </div>
            </div>

            {/* Warning message */}
            <div className="phenoconv-warning">
                <span className="text-sm">⚠️</span>
                <span className="text-xs text-[#92400E] leading-relaxed">
                    <strong>{inhibitor}</strong> is blocking {gene} activity entirely.
                    Your patient's genes are normal but the drug is making them behave as a <strong>{clinicalPhenotype}</strong>.
                </span>
            </div>
        </div>
    );
}
