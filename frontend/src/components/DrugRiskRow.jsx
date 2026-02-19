import { useState } from 'react';
import GeneTrack from './GeneTrack.jsx';
import PhenoconversionPanel from './PhenoconversionPanel.jsx';
import LLMExplanationPanel from './LLMExplanationPanel.jsx';

function riskMeta(label) {
    const l = (label || '').toLowerCase();
    if (l === 'toxic') return { accent: '#DC2626', bg: '#FEF2F2', icon: '🔴', border: '#FECACA' };
    if (l === 'ineffective') return { accent: '#D97706', bg: '#FFFBEB', icon: '🟠', border: '#FDE68A' };
    if (l.includes('adjust')) return { accent: '#2563EB', bg: '#EFF6FF', icon: '🟡', border: '#BFDBFE' };
    if (l === 'safe') return { accent: '#16A34A', bg: '#F0FDF4', icon: '🟢', border: '#BBF7D0' };
    return { accent: '#9CA3AF', bg: '#F8FAFC', icon: '⚪', border: '#E2E8F0' };
}

/**
 * DrugRiskRow — compact drug risk entry
 * Click to expand: gene track + phenoconversion + LLM explanation
 */
export default function DrugRiskRow({ result }) {
    const [expanded, setExpanded] = useState(false);

    const risk = result.risk_assessment || {};
    const pgx = result.pharmacogenomic_profile || {};
    const rec = result.clinical_recommendation || {};
    const llm = result.llm_generated_explanation || {};
    const meta = riskMeta(risk.risk_label);
    const confPct = Math.round((risk.confidence_score || 0) * 100);

    return (
        <div className="drug-risk-row-wrapper">
            {/* Summary row */}
            <button
                className="drug-risk-row"
                onClick={() => setExpanded(e => !e)}
                style={{ borderLeftColor: meta.accent }}
            >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className="text-base font-black text-[#0F172A]" style={{ fontFamily: 'Fraunces, serif' }}>
                        {result.drug}
                    </span>
                    <span className="text-xs font-mono text-[#6B7280]">
                        {pgx.primary_gene}
                    </span>
                </div>

                <div className="flex items-center gap-4">
                    {/* Risk badge */}
                    <span
                        className="text-[11px] font-bold uppercase tracking-wide px-3 py-1 rounded-full whitespace-nowrap"
                        style={{ background: meta.bg, color: meta.accent, border: `1.5px solid ${meta.border}` }}
                    >
                        {meta.icon} {risk.risk_label || 'Unknown'}
                    </span>

                    {/* Confidence */}
                    <div className="flex items-center gap-2 min-w-[100px]">
                        <div className="flex-1 h-1.5 bg-[#EFF6FF] rounded-full overflow-hidden">
                            <div
                                className="h-full rounded-full"
                                style={{
                                    width: `${confPct}%`,
                                    background: 'linear-gradient(90deg, #1E3A8A, #3B82F6)',
                                }}
                            />
                        </div>
                        <span className="text-[11px] font-mono font-bold text-[#1E3A8A] w-8 text-right">
                            {confPct}%
                        </span>
                    </div>

                    {/* Phenoconversion indicator */}
                    {risk.phenoconversion_occurred && (
                        <span className="conv-badge text-[10px]">⚡</span>
                    )}

                    {/* Expand indicator */}
                    <span className={`text-[#9CA3AF] text-xs transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}>
                        ▼
                    </span>
                </div>
            </button>

            {/* Expanded detail */}
            <div className={`drug-risk-expand ${expanded ? 'open' : ''}`}>
                <div className="drug-risk-expand-inner">
                    {/* Clinical action */}
                    <div className="mb-5">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-2">
                            Clinical Action
                        </div>
                        <div
                            className="text-sm text-[#4B5563] leading-relaxed bg-[#F8FBFF] border border-[#E2E8F0] border-l-[3px] rounded-xl p-4"
                            style={{ borderLeftColor: meta.accent }}
                        >
                            {rec.action || 'No recommendation available.'}
                        </div>
                        {(rec.alternative_drugs || []).length > 0 && (
                            <div className="flex gap-2 mt-3 flex-wrap items-center">
                                <span className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF]">Alternatives:</span>
                                {rec.alternative_drugs.map(d => (
                                    <span key={d} className="px-3 py-1 rounded-full text-xs font-mono font-semibold text-[#1E3A8A] bg-[#EFF6FF] border border-[#BFDBFE]">
                                        {d}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Gene Track */}
                    <GeneTrack
                        gene={pgx.primary_gene}
                        variants={pgx.detected_variants || []}
                    />

                    {/* Phenoconversion */}
                    {risk.phenoconversion_occurred && (
                        <div className="mt-5">
                            <PhenoconversionPanel
                                gene={pgx.primary_gene}
                                diplotype={pgx.diplotype}
                                geneticPhenotype={pgx.genetic_phenotype}
                                clinicalPhenotype={pgx.phenotype}
                                inhibitor={pgx.active_inhibitor}
                            />
                        </div>
                    )}

                    {/* LLM Explanation */}
                    <div className="mt-5">
                        <LLMExplanationPanel llm={llm} drug={result.drug} />
                    </div>
                </div>
            </div>
        </div>
    );
}
