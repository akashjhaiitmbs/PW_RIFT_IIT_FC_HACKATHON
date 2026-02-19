import { useState } from 'react';

/**
 * LLMExplanationPanel — Layer 3
 * Clinical-note styled AI explanation with purple tint.
 * Shows SUMMARY / MECHANISM / GUIDELINE / PHENOCONVERSION NOTE.
 * Footer: View Sources, Copy Note, Flag as Incorrect.
 */
export default function LLMExplanationPanel({ llm, drug, ragSourceCount = 3 }) {
    const [showSources, setShowSources] = useState(false);
    const [copied, setCopied] = useState(false);
    const [flagged, setFlagged] = useState(false);

    if (!llm) return null;

    const copyNote = () => {
        const text = [
            `SUMMARY\n${llm.summary || 'N/A'}`,
            `\nMECHANISM\n${llm.mechanism || 'N/A'}`,
            `\nGUIDELINE\n${llm.guideline_recommendation || 'N/A'}`,
            llm.phenoconversion_explanation && llm.phenoconversion_explanation !== 'Not applicable.'
                ? `\nPHENOCONVERSION NOTE\n${llm.phenoconversion_explanation}`
                : '',
        ].join('');
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const sections = [
        { key: 'summary', title: 'SUMMARY', content: llm.summary, accent: true },
        { key: 'mechanism', title: 'MECHANISM', content: llm.mechanism },
        { key: 'guideline', title: 'GUIDELINE', content: llm.guideline_recommendation, italic: true },
        {
            key: 'phenoconv',
            title: '⚡ PHENOCONVERSION NOTE',
            content: llm.phenoconversion_explanation,
            hide: !llm.phenoconversion_explanation || llm.phenoconversion_explanation === 'Not applicable.',
        },
    ];

    return (
        <div className="llm-panel">
            {/* Header */}
            <div className="llm-panel-header">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-[#312E81]">🤖 AI-Generated Explanation</span>
                    <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-[#EDE9FE] border border-[#C4B5FD] text-[#5B21B6]">
                        Azure GPT-5
                    </span>
                </div>
                <span className="text-[10px] text-[#7C3AED]">
                    Based on CPIC Guidelines · {ragSourceCount} sources retrieved
                </span>
            </div>

            {/* Sections */}
            <div className="llm-panel-body">
                {sections.map(s => {
                    if (s.hide || !s.content) return null;
                    return (
                        <div key={s.key} className="mb-4 last:mb-0">
                            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7C3AED] mb-1.5">
                                {s.title}
                            </div>
                            <div
                                className={[
                                    'text-sm leading-relaxed',
                                    s.accent
                                        ? 'font-medium text-[#1E1B4B] bg-[#EDE9FE] border border-[#C4B5FD] border-l-[3px] rounded-xl px-3 py-2.5'
                                        : 'text-[#374151]',
                                    s.italic ? 'italic bg-[#F5F3FF] border-l-[3px] border-[#C4B5FD] rounded-xl px-3 py-2.5' : '',
                                ].join(' ')}
                                style={s.accent ? { borderLeftColor: '#7C3AED' } : s.italic ? { borderLeftColor: '#7C3AED' } : {}}
                            >
                                {s.content}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Expandable sources */}
            {showSources && (
                <div className="llm-panel-sources">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-[#7C3AED] mb-2">
                        RAG Sources Retrieved
                    </div>
                    <p className="text-xs text-[#6B7280] italic">
                        Source chunks from CPIC guidelines were used to ground this explanation.
                        The deterministic risk label above is NOT influenced by the LLM.
                    </p>
                </div>
            )}

            {/* Footer buttons */}
            <div className="llm-panel-footer">
                <button
                    className="llm-btn"
                    onClick={() => setShowSources(s => !s)}
                >
                    {showSources ? '▲ Hide Sources' : '▼ View Sources'}
                </button>
                <button className="llm-btn" onClick={copyNote}>
                    {copied ? '✓ Copied' : '📋 Copy Note'}
                </button>
                <button
                    className={`llm-btn ${flagged ? 'llm-btn-flagged' : 'llm-btn-flag'}`}
                    onClick={() => setFlagged(f => !f)}
                >
                    {flagged ? '🚩 Flagged' : '⚑ Flag as Incorrect'}
                </button>
            </div>
        </div>
    );
}
