import { useState } from 'react';

const IMPACT_COLORS = {
    loss_of_function: { pin: '#DC2626', ring: '#FEE2E2', label: 'Loss of Function' },
    reduced_function: { pin: '#D97706', ring: '#FEF3C7', label: 'Reduced Function' },
    normal_function: { pin: '#9CA3AF', ring: '#F3F4F6', label: 'No Functional Change' },
};

/**
 * GeneTrack — Layer 2
 * CSS-based schematic gene track with variant pins.
 * No SVG — pure positioned divs.
 */
export default function GeneTrack({ gene, variants = [] }) {
    const [hoveredIdx, setHoveredIdx] = useState(null);

    // Simulated exon positions (relative %) for visual effect
    const exons = [
        { start: 5, width: 8 },
        { start: 18, width: 6 },
        { start: 30, width: 10 },
        { start: 48, width: 7 },
        { start: 62, width: 9 },
        { start: 78, width: 8 },
        { start: 90, width: 6 },
    ];

    // Spread variant pins evenly across the track
    const pinPositions = variants.map((_, i) => {
        const segment = 80 / Math.max(variants.length, 1);
        return 10 + i * segment + segment / 2;
    });

    return (
        <div className="gene-track-container">
            {/* Legend */}
            <div className="flex items-center gap-4 mb-3 flex-wrap">
                <span className="text-[10px] font-bold uppercase tracking-widest text-[#9CA3AF]">
                    Gene Diff Visualization
                </span>
                <div className="flex items-center gap-3 ml-auto">
                    {Object.entries(IMPACT_COLORS).map(([key, c]) => (
                        <div key={key} className="flex items-center gap-1.5">
                            <div
                                className="w-2.5 h-2.5 rounded-full"
                                style={{ background: c.pin }}
                            />
                            <span className="text-[10px] text-[#6B7280]">{c.label}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Reference track */}
            <div className="mb-1">
                <span className="text-[10px] font-mono text-[#9CA3AF]">{gene} Reference</span>
            </div>
            <div className="gene-track">
                {exons.map((ex, i) => (
                    <div
                        key={i}
                        className="gene-exon"
                        style={{ left: `${ex.start}%`, width: `${ex.width}%` }}
                    />
                ))}
            </div>

            {/* Patient track */}
            <div className="mb-1 mt-3">
                <span className="text-[10px] font-mono text-[#9CA3AF]">Patient</span>
            </div>
            <div className="gene-track gene-track-patient" style={{ position: 'relative' }}>
                {exons.map((ex, i) => (
                    <div
                        key={i}
                        className="gene-exon"
                        style={{ left: `${ex.start}%`, width: `${ex.width}%` }}
                    />
                ))}

                {/* Variant pins */}
                {variants.map((v, i) => {
                    const impact = IMPACT_COLORS[v.functional_impact] || IMPACT_COLORS.normal_function;
                    const pos = pinPositions[i];
                    return (
                        <div
                            key={i}
                            className="variant-pin-group"
                            style={{ left: `${pos}%` }}
                            onMouseEnter={() => setHoveredIdx(i)}
                            onMouseLeave={() => setHoveredIdx(null)}
                        >
                            {/* Pin stem */}
                            <div className="variant-pin-stem" />
                            {/* Pin head */}
                            <div
                                className="variant-pin-head"
                                style={{
                                    background: impact.pin,
                                    boxShadow: `0 0 0 3px ${impact.ring}`,
                                }}
                            />

                            {/* Tooltip */}
                            {hoveredIdx === i && (
                                <div className="variant-tooltip">
                                    <div className="text-[10px] font-bold text-[#1E3A8A] mb-1">
                                        {v.rsid || 'Unknown rsID'}
                                    </div>
                                    {v.chromosome && v.position && (
                                        <div className="text-[10px] text-[#6B7280] mb-0.5">
                                            {v.chromosome}:{v.position?.toLocaleString()}
                                        </div>
                                    )}
                                    <div className="text-[10px] font-mono font-bold text-[#0F172A] mb-0.5">
                                        {v.ref || '?'} → {v.alt || '?'}
                                    </div>
                                    {v.star_allele && (
                                        <div className="text-[10px] text-[#3B82F6] font-semibold mb-0.5">
                                            Defines: {v.star_allele}
                                        </div>
                                    )}
                                    <div
                                        className="text-[10px] font-semibold mt-1 pt-1 border-t border-[#E5E7EB]"
                                        style={{ color: impact.pin }}
                                    >
                                        {impact.label}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Variant labels below */}
            {variants.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                    {variants.map((v, i) => {
                        const impact = IMPACT_COLORS[v.functional_impact] || IMPACT_COLORS.normal_function;
                        return (
                            <span
                                key={i}
                                className="text-[10px] font-mono px-2 py-1 rounded-full border"
                                style={{
                                    background: impact.ring,
                                    borderColor: impact.pin,
                                    color: impact.pin,
                                }}
                            >
                                {v.rsid || '?'} · {v.ref}→{v.alt}
                                {v.star_allele ? ` · ${v.star_allele}` : ''}
                            </span>
                        );
                    })}
                </div>
            )}

            {variants.length === 0 && (
                <p className="text-xs text-[#9CA3AF] mt-3 italic">
                    No variants detected — matches reference sequence.
                </p>
            )}
        </div>
    );
}
