import { useState } from 'react';

const phenoColor = {
    PM: { bg: '#FEF2F2', border: '#FECACA', text: '#DC2626', label: 'Poor Metabolizer' },
    IM: { bg: '#FFFBEB', border: '#FDE68A', text: '#D97706', label: 'Intermediate Metabolizer' },
    NM: { bg: '#F0FDF4', border: '#BBF7D0', text: '#16A34A', label: 'Normal Metabolizer' },
    RM: { bg: '#EFF6FF', border: '#BFDBFE', text: '#2563EB', label: 'Rapid Metabolizer' },
    UM: { bg: '#FEF2F2', border: '#FECACA', text: '#DC2626', label: 'Ultrarapid Metabolizer' },
};

const fallback = { bg: '#F8FAFC', border: '#E2E8F0', text: '#64748B', label: 'Unknown' };

/**
 * GeneCard — Layer 1
 * Shows gene summary with phenotype badge. Click to expand/collapse children.
 */
export default function GeneCard({ gene, children }) {
    const [expanded, setExpanded] = useState(false);
    const p = phenoColor[gene.phenotype] || fallback;

    return (
        <div className="gene-card-wrapper">
            <button
                className="gene-card"
                onClick={() => setExpanded(e => !e)}
                style={{ borderLeftColor: p.text }}
            >
                {/* Top row */}
                <div className="flex items-center justify-between gap-3 mb-2">
                    <span className="text-lg font-black font-mono text-[#0F172A]">{gene.gene}</span>
                    <span
                        className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full"
                        style={{ background: p.bg, border: `1.5px solid ${p.border}`, color: p.text }}
                    >
                        {p.label}
                    </span>
                </div>

                {/* Diplotype */}
                <div className="text-sm font-mono font-bold text-[#1E3A8A] mb-2">
                    {gene.diplotype}
                </div>

                {/* Summary sentence */}
                <p className="text-xs text-[#4B5563] leading-relaxed mb-3">
                    {gene.summary}
                </p>

                {/* Bottom row */}
                <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium text-[#9CA3AF]">
                        {gene.variant_count} variant{gene.variant_count !== 1 ? 's' : ''} from reference
                    </span>
                    <span className="text-[10px] font-semibold text-[#3B82F6]">
                        {expanded ? '▲ Collapse' : '▼ View Diff'}
                    </span>
                </div>
            </button>

            {/* Expanded content (Layer 2 + Layer 3) */}
            <div className={`gene-card-expand ${expanded ? 'open' : ''}`}>
                <div className="gene-card-expand-inner">
                    {children}
                </div>
            </div>
        </div>
    );
}
