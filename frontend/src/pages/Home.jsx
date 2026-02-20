import Navbar from '../components/Navbar.jsx';

/* ── Feature data ── */
const FEATURES = [
    {
        icon: '🧬',
        tag: 'Genomics-First',
        title: 'Your Patient\'s DNA, Decoded Instantly',
        desc: 'Upload any VCF file and get a complete pharmacogenomic profile across 7 key metabolizer genes in seconds — no lab waiting, no manual lookup.',
    },
    {
        icon: '🤖',
        tag: 'Explainable AI',
        title: 'AI That Shows Its Work',
        desc: 'Our AI doesn\'t just give you answers — it explains the science. See exactly why a drug is flagged, what the mechanism is, and what the clinical guidelines say.',
    },
    {
        icon: '⚡',
        tag: 'Real-Time Safety',
        title: 'Catch Drug Interactions Before They Happen',
        desc: 'Our Multi-Drug Interaction Matrix detects when a co-prescribed drug shifts a patient\'s effective phenotype — turning a safe dose into a dangerous one.',
    },
    {
        icon: '🧮',
        tag: 'Interactive Dosing',
        title: 'Built-in Dose Calculator',
        desc: 'Input standard clinical doses directly into the results panel, and PharmaGuard automatically adjusts them based on the specific PGx risk modifier.',
    },
    {
        icon: '👶',
        tag: 'Clinical Demographics',
        title: 'Pediatric & Pregnancy Tailored',
        desc: 'Enzyme maturation and induction fluctuate across patient life stages. Our tool instantly flags these changes for pediatric and pregnant patients.',
    },
    {
        icon: '🔒',
        tag: 'Privacy-Ready',
        title: 'Patient Data Stays Safe',
        desc: 'Built for clinical environments. Patient data is processed securely and never used to train models. Full audit trail for every analysis.',
    },
];


/* ── Stats ── */
const STATS = [
    { value: '< 5s', label: 'To full analysis' },
    { value: '7', label: 'Genes analyzed' },
    { value: '6', label: 'Drug–gene pairs' },
    { value: '100%', label: 'Explainable AI' },
];

export default function Home({ onNavigate }) {
    return (
        <div className="min-h-screen flex flex-col bg-[#F0F6FF]">
            <Navbar onNavigate={onNavigate} currentView="home" />

            {/* ════════════════════════════════════════════
          SECTION 1 — HERO
          ════════════════════════════════════════════ */}
            <section className="relative flex flex-col items-center text-center px-6 pt-20 pb-24 overflow-hidden">
                {/* Background blobs */}
                <div className="hero-blob w-[600px] h-[400px] bg-[#BFDBFE] opacity-40 -top-20 -left-32 -z-10" style={{ position: 'absolute' }} />
                <div className="hero-blob w-[500px] h-[300px] bg-[#DBEAFE] opacity-30 top-10 -right-24 -z-10" style={{ position: 'absolute' }} />

                {/* Badge */}
                <div className="hero-badge mb-7 fade-up">
                    🏥 Built for Clinicians · Powered by AI
                </div>

                {/* Headline */}
                <h1
                    className="fade-up delay-100 max-w-4xl mb-6 text-[#0F172A]"
                    style={{ fontSize: 'clamp(2.4rem, 5.5vw, 4rem)', fontWeight: 900, lineHeight: 1.1, letterSpacing: '-0.04em' }}
                >
                    The Right Drug,{' '}
                    <span
                        className="italic"
                        style={{ color: '#1E3A8A' }}
                    >
                        for the Right Patient,
                    </span>{' '}
                    First Time.
                </h1>

                {/* Sub-copy */}
                <p
                    className="fade-up delay-200 text-[#4B5563] max-w-xl mb-10 leading-relaxed"
                    style={{ fontSize: '1.15rem', fontFamily: 'DM Sans, sans-serif', fontWeight: 400 }}
                >
                    PharmaGuard reads a patient's DNA and tells you — in seconds — which drugs to prescribe,
                    which to avoid, and exactly why. Precision medicine, finally at the point of care.
                </p>

                {/* CTAs */}
                <div className="fade-up delay-300 flex items-center gap-4 flex-wrap justify-center mb-16">
                    <button className="btn-primary text-base px-9 py-3.5" onClick={() => onNavigate('upload')}>
                        Analyze a Patient →
                    </button>
                    <button className="btn-outline text-base" onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}>
                        See How It Works
                    </button>
                </div>

                {/* Stats row */}
                <div className="fade-up delay-400 w-full max-w-3xl grid grid-cols-2 sm:grid-cols-4 gap-4">
                    {STATS.map(s => (
                        <div key={s.label} className="bg-white border border-[#E2E8F0] rounded-2xl py-5 px-4 shadow-sm">
                            <div
                                className="text-3xl font-black mb-1"
                                style={{ fontFamily: 'Fraunces, Georgia, serif', color: '#1E3A8A', letterSpacing: '-0.03em' }}
                            >
                                {s.value}
                            </div>
                            <div className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider">{s.label}</div>
                        </div>
                    ))}
                </div>

                {/* Advisory note */}
                <p className="fade-up delay-500 mt-8 text-xs text-[#9CA3AF] max-w-md">
                    For clinical decision support only. Not a substitute for professional medical judgment.
                </p>
            </section>

            {/* ════════════════════════════════════════════
          SECTION 2 — FEATURES
          ════════════════════════════════════════════ */}
            <section id="features" className="px-6 py-20 bg-white border-y border-[#E2E8F0]">
                <div className="max-w-5xl mx-auto">
                    <div className="text-center mb-14">
                        <div className="section-label mb-3">Why PharmaGuard</div>
                        <h2
                            className="text-[#0F172A] mb-4"
                            style={{ fontSize: 'clamp(1.8rem, 3.5vw, 2.8rem)', fontWeight: 800 }}
                        >
                            Stop Guessing. Start Knowing.
                        </h2>
                        <p className="text-[#4B5563] max-w-xl mx-auto" style={{ fontSize: '1.05rem' }}>
                            Over 90% of patients carry at least one pharmacogenomic variant. Most physicians
                            never know. PharmaGuard changes that.
                        </p>
                    </div>

                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {FEATURES.map((f, i) => (
                            <div key={i} className="feature-card">
                                {/* Tag */}
                                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#EFF6FF] border border-[#BFDBFE] text-[#1E3A8A] text-xs font-semibold mb-5">
                                    {f.emoji || '●'} {f.tag}
                                </div>
                                <h3
                                    className="text-[#0F172A] mb-3"
                                    style={{ fontFamily: 'Fraunces, Georgia, serif', fontSize: '1.2rem', fontWeight: 700 }}
                                >
                                    {f.title}
                                </h3>
                                <p className="text-[#4B5563] text-sm leading-relaxed">{f.desc}</p>
                            </div>
                        ))}
                    </div>

                    {/* CTA banner */}
                    <div
                        className="mt-14 rounded-2xl p-10 text-center text-white relative overflow-hidden"
                        style={{ background: 'linear-gradient(135deg, #1E3A8A 0%, #1d4ed8 100%)' }}
                    >
                        <div
                            className="absolute top-0 right-0 w-64 h-64 rounded-full opacity-10"
                            style={{ background: 'radial-gradient(circle, #fff, transparent)', transform: 'translate(30%,-30%)' }}
                        />
                        <h3 style={{ fontFamily: 'Fraunces, Georgia, serif', fontSize: '1.8rem', fontWeight: 800, marginBottom: 12 }}>
                            Ready to personalize care?
                        </h3>
                        <p className="text-blue-100 mb-7 text-base max-w-md mx-auto">
                            Upload a patient VCF file and get a complete pharmacogenomic risk report in under 5 seconds.
                        </p>
                        <button
                            className="px-10 py-3.5 rounded-xl font-semibold text-[#1E3A8A] bg-white hover:bg-blue-50 transition-colors cursor-pointer border-none text-base"
                            onClick={() => onNavigate('upload')}
                        >
                            Get Started Free →
                        </button>
                    </div>
                </div>
            </section>

            {/* ════════════════════════════════════════════
          SECTION 3 — RECOGNITION
          ════════════════════════════════════════════ */}
            <section className="px-6 py-20 pb-32">
                <div className="max-w-4xl mx-auto">
                    <div className="text-center mb-10">
                        <h2
                            className="text-[#0F172A]"
                            style={{ fontSize: 'clamp(1.8rem, 3vw, 2.6rem)', fontWeight: 800 }}
                        >
                            Recognized For Excellence
                        </h2>
                    </div>

                    {/* Hackathon badge */}
                    <div className="mt-14 flex justify-center">
                        <div className="flex items-center gap-3 px-6 py-3 bg-white border border-[#E2E8F0] rounded-2xl shadow-sm">
                            <span className="text-2xl">🏆</span>
                            <div>
                                <div className="font-bold text-[#0F172A] text-sm" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                                    PW × RIFT × IIT Hackathon
                                </div>
                                <div className="text-xs text-[#9CA3AF]">Precision Medicine Track · 2026</div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Footer ── */}
            <footer className="border-t border-[#E2E8F0] py-5 px-8 bg-white flex flex-wrap items-center justify-between gap-3 text-xs text-[#9CA3AF]">
                <span style={{ fontFamily: 'Fraunces, Georgia, serif', fontWeight: 700, color: '#1E3A8A', fontSize: '0.9rem' }}>
                    PharmaGuard
                </span>
                <span>Advisory use only · Not a medical device</span>
                <span>FastAPI · PyPGx · BioMistral · CPIC</span>
            </footer>
        </div>
    );
}
