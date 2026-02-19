import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar.jsx';
import GeneCard from '../components/GeneCard.jsx';
import GeneTrack from '../components/GeneTrack.jsx';
import PhenoconversionPanel from '../components/PhenoconversionPanel.jsx';
import DrugRiskRow from '../components/DrugRiskRow.jsx';
import { getResultsByPatient } from '../api.js';

/**
 * Results page — 3-layer progressive disclosure
 *
 * Layout:
 *   1. Header (patient info + risk summary badges)
 *   2. Gene Panel (Layer 1 gene cards expand → Layer 2 diff viz)
 *   3. Drug Risk Assessment (drug rows expand → Layer 2/3 details + LLM)
 *   4. Footer
 */
export default function Results({ results: initialResults, uploadData, genePanel: initialGenePanel, onNavigate }) {
    const [results, setResults] = useState(initialResults || []);
    const [genePanel, setGenePanel] = useState(initialGenePanel || []);
    const [fetchPatientId, setFetchPatientId] = useState('');
    const [fetching, setFetching] = useState(false);
    const [fetchError, setFetchError] = useState(null);
    const [copied, setCopied] = useState(false);
    const [activeUploadData, setActiveUploadData] = useState(uploadData);

    useEffect(() => {
        if (initialResults?.length) setResults(initialResults);
    }, [initialResults]);
    useEffect(() => {
        if (initialGenePanel?.length) setGenePanel(initialGenePanel);
    }, [initialGenePanel]);

    const copy = () => {
        navigator.clipboard.writeText(JSON.stringify(results, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleFetchByPatient = async () => {
        if (!fetchPatientId.trim()) return;
        setFetching(true);
        setFetchError(null);
        try {
            const data = await getResultsByPatient(fetchPatientId.trim());
            setResults(Array.isArray(data.results) ? data.results : [data.results]);
            setGenePanel(data.gene_panel || _buildGenePanelFallback(data.results));
            setActiveUploadData({
                patient_code: data.patient_code,
                patient_id: data.patient_id,
                total_variants_found: data.total_variants_parsed,
            });
        } catch (err) {
            setFetchError(err.message || 'Failed to fetch results.');
        } finally {
            setFetching(false);
        }
    };

    // Fallback gene panel builder from results (for the /results/{id} endpoint)
    function _buildGenePanelFallback(res) {
        const arr = Array.isArray(res) ? res : [res];
        const seen = {};
        for (const r of arr) {
            const pgx = r?.pharmacogenomic_profile || {};
            const gene = pgx.primary_gene;
            if (!gene || seen[gene]) continue;
            seen[gene] = {
                gene,
                diplotype: pgx.diplotype || 'Unknown',
                phenotype: pgx.phenotype || 'Unknown',
                genetic_phenotype: pgx.genetic_phenotype || pgx.phenotype || 'Unknown',
                active_inhibitor: pgx.active_inhibitor,
                variant_count: (pgx.detected_variants || []).length,
                summary: `${gene} metabolizer status based on detected variants`,
                variants: pgx.detected_variants || [],
            };
        }
        return Object.values(seen);
    }

    // Risk summary badges
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

                {/* ────────── Header ────────── */}
                <div className="flex flex-wrap items-start justify-between gap-4 mb-8 pb-6 border-b border-[#E2E8F0]">
                    <div>
                        <h2
                            className="text-[#0F172A] mb-1"
                            style={{ fontFamily: 'Fraunces,serif', fontWeight: 800, fontSize: '1.9rem' }}
                        >
                            Patient Risk Report
                        </h2>
                        {activeUploadData && (
                            <div className="flex flex-wrap items-center gap-3 text-sm text-[#4B5563]">
                                <span>
                                    Patient:{' '}
                                    <span className="font-mono font-bold text-[#1E3A8A]">{activeUploadData?.patient_code}</span>
                                </span>
                                <span className="text-[#9CA3AF]">·</span>
                                <span>{activeUploadData?.total_variants_found || '—'} variants parsed</span>
                            </div>
                        )}
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

                {/* ────────── Fetch by Patient ID ────────── */}
                <div className="mb-8 bg-white border border-[#E2E8F0] rounded-2xl p-5">
                    <label className="block text-xs font-bold uppercase tracking-widest text-[#9CA3AF] mb-2">
                        Fetch Results by Patient ID
                    </label>
                    <div className="flex gap-3">
                        <input
                            className="form-input flex-1"
                            value={fetchPatientId}
                            onChange={e => setFetchPatientId(e.target.value)}
                            placeholder="Enter patient code or UUID (e.g. PATIENT_001)"
                            onKeyDown={e => e.key === 'Enter' && handleFetchByPatient()}
                        />
                        <button
                            className="btn-primary text-sm px-5"
                            onClick={handleFetchByPatient}
                            disabled={fetching || !fetchPatientId.trim()}
                        >
                            {fetching ? 'Loading…' : 'Fetch'}
                        </button>
                    </div>
                    {fetchError && (
                        <p className="mt-2 text-xs text-red-600">{fetchError}</p>
                    )}
                </div>

                {results.length > 0 ? (
                    <>
                        {/* ────────── Section 1: Gene Panel ────────── */}
                        {genePanel.length > 0 && (
                            <section className="mb-10">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="h-px flex-1 bg-[#E2E8F0]" />
                                    <span className="section-label">🧬 Gene Panel</span>
                                    <div className="h-px flex-1 bg-[#E2E8F0]" />
                                </div>
                                <div
                                    className="grid gap-4"
                                    style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}
                                >
                                    {genePanel.map(g => (
                                        <GeneCard key={g.gene} gene={g}>
                                            <GeneTrack gene={g.gene} variants={g.variants || []} />
                                            {g.active_inhibitor && (
                                                <div className="mt-4">
                                                    <PhenoconversionPanel
                                                        gene={g.gene}
                                                        diplotype={g.diplotype}
                                                        geneticPhenotype={g.genetic_phenotype}
                                                        clinicalPhenotype={g.phenotype}
                                                        inhibitor={g.active_inhibitor}
                                                    />
                                                </div>
                                            )}
                                        </GeneCard>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* ────────── Section 2: Drug Risk Assessment ────────── */}
                        <section className="mb-10">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="h-px flex-1 bg-[#E2E8F0]" />
                                <span className="section-label">💊 Drug Risk Assessment</span>
                                <div className="h-px flex-1 bg-[#E2E8F0]" />
                            </div>
                            <div className="flex flex-col gap-3">
                                {results.map((r, i) => (
                                    <DrugRiskRow key={i} result={r} />
                                ))}
                            </div>
                        </section>

                        {/* ────────── Raw JSON ────────── */}
                        <div className="bg-white border border-[#E2E8F0] rounded-2xl overflow-hidden">
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
                    </>
                ) : (
                    <div className="text-center py-20 text-[#9CA3AF]">
                        <div className="text-4xl mb-3">🔬</div>
                        <p className="text-sm">No results yet. Run an analysis or fetch by patient ID above.</p>
                    </div>
                )}
            </div>

            <footer className="border-t border-[#E2E8F0] py-4 px-8 bg-white flex flex-wrap items-center justify-between gap-3 text-xs text-[#9CA3AF] mt-auto">
                <span style={{ fontFamily: 'Fraunces,serif', fontWeight: 700, color: '#1E3A8A', fontSize: '0.88rem' }}>
                    PharmaGuard
                </span>
                <span>Advisory use only · Not a medical device</span>
                <span>FastAPI · PyPGx · Azure GPT-5 · CPIC</span>
            </footer>
        </div>
    );
}
