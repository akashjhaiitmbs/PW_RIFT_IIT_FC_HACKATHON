import { useState } from 'react';
import Navbar from '../components/Navbar.jsx';
import DrugCard from '../components/DrugCard.jsx';

export default function Results({ results, uploadData, onNavigate }) {
    const [copied, setCopied] = useState(false);

    const copy = () => {
        navigator.clipboard.writeText(JSON.stringify(results, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const counts = results.reduce((acc, r) => {
        const l = (r.risk_assessment?.risk_label || '').toLowerCase();
        if (l === 'toxic' || l === 'ineffective') acc.critical++;
        else if (l.includes('adjust')) acc.warn++;
        else if (l === 'safe') acc.safe++;
        return acc;
    }, { critical: 0, warn: 0, safe: 0 });

    return (
        <div className="min-h-screen flex flex-col bg-[#F0F6FF]">
            <Navbar onNavigate={onNavigate} currentView="results" />

            <div className="flex-1 px-6 py-8 max-w-7xl mx-auto w-full">

                {/* ── Header ── */}
                <div className="flex flex-wrap items-start justify-between gap-4 mb-8 pb-6 border-b border-[#E2E8F0]">
                    <div>
                        <h2
                            className="text-[#0F172A] mb-1"
                            style={{ fontFamily: 'Fraunces,serif', fontWeight: 800, fontSize: '1.9rem' }}
                        >
                            Patient Risk Report
                        </h2>
                        <div className="flex flex-wrap items-center gap-3 text-sm text-[#4B5563]">
                            <span>
                                Patient:{' '}
                                <span className="font-mono font-bold text-[#1E3A8A]">{uploadData?.patient_code}</span>
                            </span>
                            <span className="text-[#9CA3AF]">·</span>
                            <span>{uploadData?.total_variants_found || '—'} variants parsed</span>
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {counts.critical > 0 && (
                            <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-red-50 border border-red-200 text-red-700">
                                ☠️ {counts.critical} High Risk
                            </span>
                        )}
                        {counts.warn > 0 && (
                            <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700">
                                💊 {counts.warn} Adjust Dose
                            </span>
                        )}
                        {counts.safe > 0 && (
                            <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-green-50 border border-green-200 text-green-700">
                                ✅ {counts.safe} Safe
                            </span>
                        )}
                        <button className="btn-ghost text-xs" onClick={copy}>
                            {copied ? '✓ Copied' : '📋 Copy JSON'}
                        </button>
                        <button className="btn-ghost text-xs" onClick={() => onNavigate('upload')}>
                            + New Analysis
                        </button>
                    </div>
                </div>

                {/* ── Drug cards grid ── */}
                <div
                    className="grid gap-5"
                    style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}
                >
                    {results.map((r, i) => <DrugCard key={i} result={r} />)}
                </div>

                {/* ── JSON viewer ── */}
                <div className="mt-10 bg-white border border-[#E2E8F0] rounded-2xl overflow-hidden">
                    <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#E2E8F0] bg-[#F8FBFF]">
                        <span className="text-xs font-bold uppercase tracking-widest text-[#9CA3AF]">
                            Raw JSON Output
                        </span>
                        <button className="btn-ghost text-xs py-1.5 px-3" onClick={copy}>
                            {copied ? '✓ Copied' : 'Copy'}
                        </button>
                    </div>
                    <pre className="p-5 text-xs font-mono text-[#4B5563] leading-relaxed overflow-x-auto max-h-72">
                        {JSON.stringify(results, null, 2)}
                    </pre>
                </div>
            </div>

            <footer className="border-t border-[#E2E8F0] py-4 px-8 bg-white flex flex-wrap items-center justify-between gap-3 text-xs text-[#9CA3AF] mt-auto">
                <span style={{ fontFamily: 'Fraunces,serif', fontWeight: 700, color: '#1E3A8A', fontSize: '0.88rem' }}>
                    PharmaGuard
                </span>
                <span>Advisory use only · Not a medical device</span>
                <span>FastAPI · PyPGx · BioMistral · CPIC</span>
            </footer>
        </div>
    );
}
