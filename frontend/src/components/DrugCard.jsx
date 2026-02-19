import { useState } from 'react';

function riskMeta(label) {
    const l = (label || '').toLowerCase();
    if (l === 'toxic') return { cls: 'risk-toxic', accent: '#DC2626', bg: '#FEF2F2', icon: '☠️' };
    if (l === 'ineffective') return { cls: 'risk-ineffective', accent: '#D97706', bg: '#FFFBEB', icon: '⚠️' };
    if (l.includes('adjust')) return { cls: 'risk-adjust', accent: '#2563EB', bg: '#EFF6FF', icon: '💊' };
    if (l === 'safe') return { cls: 'risk-safe', accent: '#16A34A', bg: '#F0FDF4', icon: '✅' };
    return { cls: 'risk-unknown', accent: '#9CA3AF', bg: '#F8FAFC', icon: '❓' };
}

function severityColor(s) {
    const m = { critical: '#DC2626', high: '#EA580C', moderate: '#D97706', low: '#16A34A', none: '#16A34A' };
    return m[(s || '').toLowerCase()] || '#9CA3AF';
}

function phenoBadge(p) {
    if (p === 'PM' || p === 'IM') return 'bg-red-50 text-red-600 border border-red-200';
    if (p === 'NM') return 'bg-green-50 text-green-700 border border-green-200';
    if (p === 'UM' || p === 'RM') return 'bg-amber-50 text-amber-700 border border-amber-200';
    return 'bg-[#EFF6FF] text-[#1E3A8A] border border-[#BFDBFE]';
}

/* ── Accordion ── */
function Accordion({ title, children, defaultOpen = false }) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="border border-[#E2E8F0] rounded-xl overflow-hidden">
            <button
                className="w-full flex items-center justify-between px-4 py-3.5 bg-[#F8FBFF] hover:bg-[#EFF6FF] transition-colors text-sm font-semibold text-[#0F172A] text-left cursor-pointer border-none"
                onClick={() => setOpen(o => !o)}
            >
                <span>{title}</span>
                <svg className={`accordion-chevron ${open ? 'open' : ''} w-4 h-4 text-[#9CA3AF]`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            </button>
            <div className={`accordion-body ${open ? 'open' : ''}`}>
                <div className="px-4 pb-4 pt-3 border-t border-[#E2E8F0] bg-white">
                    {children}
                </div>
            </div>
        </div>
    );
}

/* ── Confidence bar ── */
function ConfBar({ value }) {
    const pct = Math.round((value || 0) * 100);
    return (
        <div className="flex flex-col gap-1.5">
            <div className="flex justify-between text-xs font-medium text-[#4B5563]">
                <span>Confidence Score</span>
                <span className="font-mono font-bold text-[#1E3A8A]">{pct}%</span>
            </div>
            <div className="h-1.5 bg-[#EFF6FF] rounded-full overflow-hidden">
                <div className="conf-bar-fill" style={{ width: `${pct}%` }} />
            </div>
        </div>
    );
}

/* ── Drug Card ── */
export default function DrugCard({ result }) {
    const risk = result.risk_assessment || {};
    const pgx = result.pharmacogenomic_profile || {};
    const rec = result.clinical_recommendation || {};
    const llm = result.llm_generated_explanation || {};
    const qm = result.quality_metrics || {};
    const meta = riskMeta(risk.risk_label);
    const pheno = pgx.phenotype || '?';
    const converted = qm.phenoconversion_detected;

    return (
        <div className="drug-card flex flex-col" style={{ borderTop: `3px solid ${meta.accent}` }}>

            {/* ── Header ── */}
            <div className="drug-card-top" style={{ background: meta.bg }}>
                <div className="flex items-start justify-between gap-2 mb-3 flex-wrap">
                    <div
                        className="text-xl font-black text-[#0F172A]"
                        style={{ fontFamily: 'Fraunces, Georgia, serif', letterSpacing: '-0.03em' }}
                    >
                        {result.drug}
                    </div>
                    <span className={`risk-badge ${meta.cls}`}>
                        {meta.icon} {risk.risk_label || 'Unknown'}
                    </span>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2.5 py-0.5 rounded-full bg-[#EFF6FF] border border-[#BFDBFE] text-xs font-mono font-bold text-[#1E3A8A]">
                        {pgx.primary_gene}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold ${phenoBadge(pheno)}`}>
                        {pheno}
                    </span>
                    {converted && <span className="conv-badge">⚡ Phenoconverted</span>}
                    <span className="ml-auto text-xs font-semibold" style={{ color: severityColor(risk.severity) }}>
                        {(risk.severity || '').toUpperCase() || '—'}
                    </span>
                </div>
            </div>

            {/* ── Body ── */}
            <div className="p-5 flex flex-col gap-4 flex-1">

                <ConfBar value={risk.confidence_score} />

                {/* Info grid */}
                <div className="grid grid-cols-2 gap-2">
                    <div className="info-cell">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-1">Diplotype</div>
                        <div className="text-sm font-bold font-mono text-[#0F172A]">{pgx.diplotype || '—'}</div>
                    </div>
                    <div className="info-cell">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-1">Evidence</div>
                        <div className="text-sm font-bold font-mono text-[#0F172A]">{rec.evidence_level || '—'}</div>
                    </div>
                </div>

                {/* Dosing */}
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="h-px flex-1 bg-[#E2E8F0]" />
                        <span className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF]">Clinical Action</span>
                        <div className="h-px flex-1 bg-[#E2E8F0]" />
                    </div>
                    <div
                        className="bg-[#F8FBFF] border border-[#E2E8F0] border-l-[3px] rounded-xl p-4 text-sm text-[#4B5563] leading-relaxed"
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

                {/* AI Explanation */}
                <Accordion title={
                    <span className="flex items-center gap-2">
                        🤖 AI Explanation
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-bold text-[#1E3A8A] bg-[#EFF6FF] border border-[#BFDBFE]">
                            BioMistral
                        </span>
                    </span>
                }>
                    <div className="flex flex-col gap-3">
                        {llm.summary && (
                            <div>
                                <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-1.5">Summary</div>
                                <div className="text-sm text-[#0F172A] font-medium leading-relaxed px-3 py-2.5 bg-[#EFF6FF] border border-[#BFDBFE] border-l-[3px] rounded-xl"
                                    style={{ borderLeftColor: '#1E3A8A' }}>
                                    {llm.summary}
                                </div>
                            </div>
                        )}
                        {llm.mechanism && (
                            <div>
                                <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-1.5">Mechanism</div>
                                <div className="text-sm text-[#4B5563] leading-relaxed">{llm.mechanism}</div>
                            </div>
                        )}
                        {llm.guideline_recommendation && (
                            <div>
                                <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-1.5">Guideline</div>
                                <div className="text-sm text-[#4B5563] leading-relaxed italic px-3 py-2.5 bg-[#F8FBFF] border-l-[3px] border-[#BFDBFE] rounded-xl">
                                    {llm.guideline_recommendation}
                                </div>
                            </div>
                        )}
                        {llm.phenoconversion_explanation && llm.phenoconversion_explanation !== 'Not applicable.' && (
                            <div>
                                <div className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF] mb-1.5">⚡ Phenoconversion</div>
                                <div className="text-sm text-[#4B5563] leading-relaxed">{llm.phenoconversion_explanation}</div>
                            </div>
                        )}
                    </div>
                </Accordion>

                {/* Detected variants */}
                {(pgx.detected_variants || []).length > 0 && (
                    <Accordion title={`🔬 Detected Variants (${pgx.detected_variants.length})`}>
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs font-mono">
                                <thead>
                                    <tr className="text-[#9CA3AF] text-left">
                                        {['rsID', 'Position', 'Ref/Alt', 'GT', 'Star', 'Filter'].map(h => (
                                            <th key={h} className="pb-2 pr-3 font-semibold uppercase tracking-wider text-[9px]">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {pgx.detected_variants.slice(0, 10).map((v, i) => (
                                        <tr key={i} className="border-t border-[#E2E8F0] hover:bg-[#F8FBFF]">
                                            <td className="py-1.5 pr-3 text-[#1E3A8A] font-bold">{v.rsid || '.'}</td>
                                            <td className="py-1.5 pr-3 text-[#4B5563]">{v.position?.toLocaleString()}</td>
                                            <td className="py-1.5 pr-3 text-[#0F172A] font-bold">{v.ref}/{v.alt}</td>
                                            <td className="py-1.5 pr-3 text-[#4B5563]">{v.genotype}</td>
                                            <td className="py-1.5 pr-3 text-[#3B82F6]">{v.star_allele || '—'}</td>
                                            <td className={`py-1.5 font-bold ${v.filter === 'PASS' ? 'text-green-600' : 'text-amber-600'}`}>{v.filter}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </Accordion>
                )}
            </div>

            {/* ── Quality footer ── */}
            <div className="flex flex-wrap gap-2 px-4 py-3 border-t border-[#E2E8F0] bg-[#F8FBFF]">
                <span className="text-[10px] font-medium px-2.5 py-1 rounded-full bg-white border border-[#E2E8F0] text-[#4B5563]">
                    {qm.vcf_parsing_success ? '✅' : '❌'} VCF
                </span>
                <span className="text-[10px] font-medium px-2.5 py-1 rounded-full bg-white border border-[#E2E8F0] text-[#4B5563]">
                    {qm.variants_detected || 0} variants
                </span>
                <span className="text-[10px] font-medium px-2.5 py-1 rounded-full bg-white border border-[#E2E8F0] text-[#4B5563]">
                    {(qm.genes_called_successfully || []).length}/7 genes
                </span>
                {converted && (
                    <span className="text-[10px] font-medium px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700">
                        ⚡ Converted
                    </span>
                )}
                <span className="ml-auto text-[10px] font-mono font-bold px-2.5 py-1 rounded-full bg-[#EFF6FF] border border-[#BFDBFE] text-[#1E3A8A]">
                    {((risk.confidence_score || 0) * 100).toFixed(0)}% conf
                </span>
            </div>
        </div>
    );
}
