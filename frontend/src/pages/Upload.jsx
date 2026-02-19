import { useState, useRef, useCallback } from 'react';
import Navbar from '../components/Navbar.jsx';
import { analyzeVCF } from '../api.js';

const SUPPORTED_DRUGS = ['CODEINE', 'WARFARIN', 'CLOPIDOGREL', 'SIMVASTATIN', 'AZATHIOPRINE', 'FLUOROURACIL'];
const KNOWN_MEDS = ['PAROXETINE', 'FLUOXETINE', 'BUPROPION', 'DULOXETINE', 'TERBINAFINE', 'OMEPRAZOLE', 'FLUVOXAMINE', 'RIFAMPIN', 'FLUCONAZOLE', 'AMIODARONE'];

const PIPELINE_STEPS = [
    { id: 1, label: 'Uploading & parsing VCF file' },
    { id: 2, label: 'Calling genotyper across 7 genes' },
    { id: 3, label: 'Computing metabolizer activity scores' },
    { id: 4, label: 'Checking drug interaction effects' },
    { id: 5, label: 'Matching CPIC clinical guidelines' },
    { id: 6, label: 'Generating confidence score' },
    { id: 7, label: 'Drafting AI-powered explanation' },
];

function PipelineLoader({ step }) {
    return (
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-16">
            <div
                className="w-full max-w-md bg-white border border-[#E2E8F0] rounded-3xl p-10"
                style={{ boxShadow: '0 8px 40px rgba(30,58,138,0.1)' }}
            >
                <div className="text-center mb-8">
                    <div
                        className="w-14 h-14 rounded-2xl flex items-center justify-center text-white text-xl font-bold mx-auto mb-4"
                        style={{ background: '#1E3A8A' }}
                    >
                        Rx
                    </div>
                    <div
                        className="text-xl font-bold text-[#0F172A] mb-1"
                        style={{ fontFamily: 'Fraunces, Georgia, serif' }}
                    >
                        Analyzing Patient Profile
                    </div>
                    <div className="text-sm text-[#9CA3AF]">Full pipeline in progress…</div>
                </div>

                <div className="flex flex-col gap-2.5">
                    {PIPELINE_STEPS.map(s => {
                        const state = s.id < step ? 'done' : s.id === step ? 'active' : 'pending';
                        return (
                            <div
                                key={s.id}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${state === 'done' ? 'bg-green-50 border border-green-200' :
                                    state === 'active' ? 'bg-[#EFF6FF] border border-[#BFDBFE]' :
                                        'border border-transparent opacity-40'
                                    }`}
                            >
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${state === 'done' ? 'bg-green-100 text-green-600' :
                                    state === 'active' ? 'bg-[#DBEAFE] text-[#1E3A8A] step-spin' :
                                        'bg-[#F0F6FF] text-[#9CA3AF]'
                                    }`}>
                                    {state === 'done' ? '✓' : state === 'active' ? '↻' : s.id}
                                </div>
                                <span className={`text-sm font-medium ${state === 'done' ? 'text-green-700' :
                                    state === 'active' ? 'text-[#1E3A8A]' :
                                        'text-[#9CA3AF]'
                                    }`}>
                                    {s.label}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

export default function Upload({ onNavigate, onResults }) {
    const [file, setFile] = useState(null);
    const [dragging, setDragging] = useState(false);
    const [patientCode, setPatientCode] = useState('PATIENT_001');
    const [selectedDrugs, setSelectedDrugs] = useState([]);
    const [selectedMeds, setSelectedMeds] = useState([]);
    const [loading, setLoading] = useState(false);
    const [pipelineStep, setPipelineStep] = useState(0);
    const [toast, setToast] = useState(null);
    const fileRef = useRef();

    const showToast = (msg) => {
        setToast(msg);
        setTimeout(() => setToast(null), 4000);
    };

    const handleDrop = useCallback(e => {
        e.preventDefault(); setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f?.name.endsWith('.vcf')) setFile(f);
        else showToast('Please upload a .vcf file.');
    }, []);

    const toggleDrug = d => setSelectedDrugs(p => p.includes(d) ? p.filter(x => x !== d) : [...p, d]);
    const toggleMed = m => setSelectedMeds(p => p.includes(m) ? p.filter(x => x !== m) : [...p, m]);
    const toggleAll = () => setSelectedDrugs(selectedDrugs.length === SUPPORTED_DRUGS.length ? [] : [...SUPPORTED_DRUGS]);

    const handleSubmit = async () => {
        if (!file) return showToast('Please select a VCF file.');
        if (selectedDrugs.length === 0) return showToast('Select at least one drug to analyze.');

        setLoading(true);
        setPipelineStep(1);

        // Simulate pipeline progress while the single API call runs
        let step = 1;
        const ticker = setInterval(() => {
            step = Math.min(step + 1, 6);
            setPipelineStep(step);
        }, 700);

        try {
            // Single call — uploads VCF + runs analysis in one request
            const data = await analyzeVCF({
                file,
                patientCode,
                drugs: selectedDrugs,
                concurrentMedications: selectedMeds,
            });

            clearInterval(ticker);
            setPipelineStep(7);
            await new Promise(r => setTimeout(r, 600));

            const results = Array.isArray(data.results) ? data.results : [data.results];
            onResults(results, {
                patient_code: data.patient_code,
                patient_id: data.patient_id,
                total_variants_found: data.total_variants_parsed,
            }, data.gene_panel || []);
        } catch (err) {
            clearInterval(ticker);
            showToast(err.message || 'Analysis failed. Check console.');
            setLoading(false);
            setPipelineStep(0);
        }
    };

    if (loading) return (
        <div className="min-h-screen flex flex-col bg-[#F0F6FF]">
            <Navbar onNavigate={onNavigate} currentView="upload" />
            <PipelineLoader step={pipelineStep} />
        </div>
    );

    return (
        <div className="min-h-screen flex flex-col bg-[#F0F6FF]">
            <Navbar onNavigate={onNavigate} currentView="upload" />

            <div className="flex-1 px-6 py-12">
                <div className="max-w-xl mx-auto flex flex-col gap-6">

                    {/* Page title */}
                    <div className="text-center mb-2">
                        <h2
                            className="text-[#0F172A] mb-2"
                            style={{ fontFamily: 'Fraunces, Georgia, serif', fontWeight: 800, fontSize: '2rem' }}
                        >
                            Upload Patient VCF
                        </h2>
                        <p className="text-[#4B5563] text-sm">Provide a VCF, select drugs — get a full risk report in seconds</p>
                    </div>

                    {/* ── Dropzone ── */}
                    <div
                        className={`dropzone px-8 py-14 text-center ${dragging ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
                        onDragOver={e => { e.preventDefault(); setDragging(true) }}
                        onDragLeave={() => setDragging(false)}
                        onDrop={handleDrop}
                        onClick={() => fileRef.current.click()}
                        role="button" tabIndex={0}
                        onKeyDown={e => e.key === 'Enter' && fileRef.current.click()}
                    >
                        <input ref={fileRef} type="file" accept=".vcf" className="hidden"
                            onChange={e => { const f = e.target.files[0]; if (f) setFile(f) }} />
                        <div className="text-5xl mb-3">{file ? '✅' : '📄'}</div>
                        {file
                            ? <>
                                <div className="font-semibold text-green-600 text-base mb-1">{file.name}</div>
                                <div className="text-xs text-[#9CA3AF]">{(file.size / 1024).toFixed(1)} KB · click to change</div>
                            </>
                            : <>
                                <div className="font-semibold text-[#0F172A] mb-1">Drop your VCF file here</div>
                                <div className="text-xs text-[#9CA3AF]">or click to browse · .vcf format · max 5 MB</div>
                            </>
                        }
                    </div>

                    {/* ── Patient code ── */}
                    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5">
                        <label className="block text-xs font-bold uppercase tracking-widest text-[#9CA3AF] mb-2 font-['DM_Sans']">
                            Patient Identifier
                        </label>
                        <input
                            className="form-input"
                            value={patientCode}
                            onChange={e => setPatientCode(e.target.value)}
                            placeholder="e.g. PATIENT_001"
                        />
                    </div>

                    {/* ── Drug selector ── */}
                    <div className="bg-white border border-[#E2E8F0] rounded-2xl overflow-hidden">
                        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E2E8F0]">
                            <div>
                                <h3 className="text-[#0F172A] text-base font-semibold mb-0.5" style={{ fontFamily: 'Fraunces,serif' }}>Select Drugs</h3>
                                <p className="text-xs text-[#9CA3AF]">{selectedDrugs.length} of {SUPPORTED_DRUGS.length} selected</p>
                            </div>
                            <button className="text-xs font-semibold text-[#3B82F6] hover:text-[#1E3A8A] transition-colors bg-transparent border-none cursor-pointer" onClick={toggleAll}>
                                {selectedDrugs.length === SUPPORTED_DRUGS.length ? 'Clear all' : 'Select all'}
                            </button>
                        </div>
                        <div className="px-5 py-4 flex flex-wrap gap-2">
                            {SUPPORTED_DRUGS.map(d => (
                                <button key={d} className={`pill-toggle ${selectedDrugs.includes(d) ? 'active' : ''}`} onClick={() => toggleDrug(d)}>
                                    {d}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* ── Co-medications ── */}
                    <div className="bg-white border border-[#E2E8F0] rounded-2xl overflow-hidden">
                        <div className="px-5 py-4 border-b border-[#E2E8F0]">
                            <h3 className="text-[#0F172A] text-base font-semibold mb-0.5" style={{ fontFamily: 'Fraunces,serif' }}>Co-medications</h3>
                            <p className="text-xs text-[#9CA3AF]">Select concurrent drugs to detect interaction effects</p>
                        </div>
                        <div className="px-5 py-4 flex flex-wrap gap-2">
                            {KNOWN_MEDS.map(m => (
                                <button key={m} className={`pill-toggle text-xs ${selectedMeds.includes(m) ? 'med-active' : ''}`} onClick={() => toggleMed(m)}>
                                    {m}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* ── Submit ── */}
                    <button
                        className="btn-primary justify-center text-base py-4 w-full"
                        onClick={handleSubmit}
                        disabled={!file || selectedDrugs.length === 0}
                    >
                        Run Full Analysis →
                    </button>

                    <p className="text-center text-xs text-[#9CA3AF]">
                        For clinical decision support only · Results generated in &lt;5 seconds
                    </p>
                </div>
            </div>

            {/* Toast */}
            {toast && (
                <div className="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl text-sm font-medium toast-enter max-w-xs bg-red-50 border border-red-200 text-red-700 shadow-md">
                    {toast}
                </div>
            )}
        </div>
    );
}
