export default function Navbar({ onNavigate, currentView }) {
    return (
        <nav className="glass-nav sticky top-0 z-50 flex items-center justify-between px-8 py-4">
            {/* Logo */}
            <button
                onClick={() => onNavigate('home')}
                className="flex items-center gap-3 border-none bg-transparent cursor-pointer"
            >
                <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-base font-bold"
                    style={{ background: '#1E3A8A', boxShadow: '0 2px 8px rgba(30,58,138,0.3)' }}
                >
                    Rx
                </div>
                <span
                    className="text-lg font-bold tracking-tight"
                    style={{ fontFamily: 'Fraunces, Georgia, serif', color: '#1E3A8A' }}
                >
                    PharmaGuard
                </span>
            </button>

            {/* Right side */}
            <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EFF6FF] border border-[#BFDBFE] text-xs font-semibold text-[#1E3A8A]">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 dot-pulse inline-block" />
                    AI Engine Live
                </div>

                {currentView === 'home' ? (
                    <button className="btn-primary py-2.5 px-5 text-sm" onClick={() => onNavigate('upload')}>
                        Upload VCF →
                    </button>
                ) : (
                    <button className="btn-ghost" onClick={() => onNavigate('home')}>
                        ← Home
                    </button>
                )}
            </div>
        </nav>
    );
}
