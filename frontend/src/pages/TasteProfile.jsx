import React, { useState, useEffect, useMemo } from 'react';
import { getTasteProfile } from '../api';

// ── Radar chart geometry helpers ───────────────────────────────────────────
const LABELS = ['Energy', 'Valence', 'Tempo', 'Acousticness', 'Instrumentalness', 'Speechiness', 'Danceability'];
const CENTER = 250;
const RADIUS = 200;
const RINGS = [0.25, 0.5, 0.75, 1.0];

function polarToCartesian(angle, value) {
    const r = RADIUS * value;
    const x = CENTER + r * Math.sin(angle);
    const y = CENTER - r * Math.cos(angle);
    return { x, y };
}

function getAngle(index) {
    return (2 * Math.PI * index) / LABELS.length;
}

// ── Radar Chart Component ──────────────────────────────────────────────────
function RadarChart({ features, animated }) {
    const values = LABELS.map(l => features[l.toLowerCase()] || 0);

    const points = values.map((v, i) => polarToCartesian(getAngle(i), v));
    const polygon = points.map(p => `${p.x},${p.y}`).join(' ');

    // Grid ring polygons
    const gridRings = RINGS.map(ringVal => {
        const ringPoints = LABELS.map((_, i) => {
            const p = polarToCartesian(getAngle(i), ringVal);
            return `${p.x},${p.y}`;
        });
        return ringPoints.join(' ');
    });

    // Axis lines
    const axes = LABELS.map((_, i) => {
        const p = polarToCartesian(getAngle(i), 1.0);
        return { x2: p.x, y2: p.y };
    });

    // Label positions (pushed outward)
    const labelPositions = LABELS.map((label, i) => {
        const p = polarToCartesian(getAngle(i), 1.18);
        return { label, x: p.x, y: p.y };
    });

    return (
        <svg viewBox="0 0 500 500" className="w-full max-w-[500px] overflow-visible">
            <defs>
                <linearGradient id="radarFill" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#72fe8f" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#1cb853" stopOpacity="0.15" />
                </linearGradient>
                <filter id="glow">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>

            {/* Grid rings */}
            {gridRings.map((ring, i) => (
                <polygon key={i} points={ring} fill="none" stroke="#262626" strokeWidth="1" />
            ))}

            {/* Axis lines */}
            {axes.map((a, i) => (
                <line key={i} x1={CENTER} y1={CENTER} x2={a.x2} y2={a.y2}
                    stroke="#262626" strokeWidth="1" />
            ))}

            {/* Data polygon */}
            <polygon
                points={polygon}
                fill="url(#radarFill)"
                stroke="#72fe8f"
                strokeWidth="2"
                strokeOpacity="0.8"
                filter="url(#glow)"
                className={animated ? 'animate-radar-draw' : ''}
            />

            {/* Data points */}
            {points.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r="4" fill="#72fe8f"
                    className={animated ? 'animate-fade-in' : ''}
                    style={{ animationDelay: `${i * 0.1}s` }} />
            ))}

            {/* Labels */}
            {labelPositions.map(({ label, x, y }, i) => (
                <text key={i} x={x} y={y}
                    textAnchor="middle" dominantBaseline="middle"
                    className="fill-[#adaaaa] text-[0.6rem] uppercase tracking-[0.1em] font-bold"
                    style={{ fontFamily: 'Inter, sans-serif' }}>
                    {label}
                </text>
            ))}
        </svg>
    );
}

// ── Progress Bar Component ─────────────────────────────────────────────────
function FeatureBar({ label, value, delay = 0 }) {
    const pct = Math.round(value * 100);
    return (
        <div className="space-y-3">
            <div className="flex justify-between items-end">
                <span className="text-sm font-medium text-white">{label}</span>
                <span className="text-sm font-bold text-[#72fe8f]">{pct}%</span>
            </div>
            <div className="h-1.5 w-full bg-[#262626] rounded-full overflow-hidden">
                <div
                    className="h-full rounded-full transition-all duration-1000 ease-out"
                    style={{
                        width: `${pct}%`,
                        background: 'linear-gradient(135deg, #72fe8f 0%, #1cb853 100%)',
                        transitionDelay: `${delay}ms`,
                    }}
                />
            </div>
        </div>
    );
}

// ── Main Component ─────────────────────────────────────────────────────────
export default function TasteProfile() {
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadProfile() {
            try {
                const res = await getTasteProfile();
                setProfile(res.data);
            } catch (err) {
                console.error('Failed to load taste profile:', err);
                setError('Unable to load your taste profile. Play some music first!');
            } finally {
                setLoading(false);
            }
        }
        loadProfile();
    }, []);

    if (loading) {
        return (
            <div className="p-12 flex items-center justify-center min-h-screen">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-2 border-[#72fe8f] border-t-transparent rounded-full animate-spin" />
                    <p className="text-[#adaaaa] text-sm">Loading your sonic DNA...</p>
                </div>
            </div>
        );
    }

    if (error || !profile) {
        return (
            <div className="p-12">
                <p className="text-[#adaaaa]">{error || 'No profile data available.'}</p>
            </div>
        );
    }

    const features = profile.features || {};

    return (
        <div className="min-h-screen">
            {/* Header */}
            <header className="pt-16 pb-8 px-12 max-w-7xl mx-auto">
                <h2 className="text-[3.5rem] font-['Plus_Jakarta_Sans'] font-extrabold tracking-[-0.04em] leading-tight text-white">
                    Your Sonic DNA
                </h2>
                <p className="text-lg text-[#adaaaa] max-w-2xl mt-4" style={{ fontFamily: 'Inter, sans-serif' }}>
                    A visual fingerprint of your listening personality
                </p>
            </header>

            {/* Radar Chart */}
            <section className="flex flex-col items-center justify-center py-12 relative overflow-hidden">
                {/* Glow background */}
                <div className="absolute w-[600px] h-[600px] bg-[#72fe8f]/5 rounded-full blur-[120px] -z-10" />
                <div className="relative w-full max-w-[500px] px-8">
                    <RadarChart features={features} animated={true} />
                </div>
            </section>

            {/* Stat Cards */}
            <section className="px-12 pb-16 max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Dominant Mood */}
                <div className="bg-[#1a1a1a] rounded-2xl p-8 flex items-center gap-6 transition-colors duration-300 hover:bg-[#2c2c2c] group">
                    <div className="w-16 h-16 rounded-full bg-[#262626] flex items-center justify-center text-[#72fe8f] group-hover:scale-110 transition-transform duration-300">
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m13 2 3 14h-9l3-14"/><path d="m5 16 3 6h8l3-6"/></svg>
                    </div>
                    <div>
                        <p className="text-[0.6875rem] uppercase tracking-wider text-[#adaaaa] font-medium">Dominant Mood</p>
                        <p className="text-2xl font-bold font-['Plus_Jakarta_Sans'] text-white mt-1">
                            {profile.dominant_mood || 'Balanced'}
                        </p>
                    </div>
                </div>

                {/* Avg BPM */}
                <div className="bg-[#1a1a1a] rounded-2xl p-8 flex items-center gap-6 transition-colors duration-300 hover:bg-[#2c2c2c] group">
                    <div className="w-16 h-16 rounded-full bg-[#262626] flex items-center justify-center text-[#72fe8f] group-hover:scale-110 transition-transform duration-300">
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                    </div>
                    <div>
                        <p className="text-[0.6875rem] uppercase tracking-wider text-[#adaaaa] font-medium">Avg BPM</p>
                        <div className="flex items-baseline gap-1 mt-1">
                            <span className="text-3xl font-black font-['Plus_Jakarta_Sans'] text-white">{profile.avg_bpm || '—'}</span>
                            <span className="text-sm font-medium text-[#adaaaa]">bpm</span>
                        </div>
                    </div>
                </div>

                {/* Vibe Type */}
                <div className="bg-[#1a1a1a] rounded-2xl p-8 flex items-center gap-6 transition-colors duration-300 hover:bg-[#2c2c2c] group">
                    <div className="w-16 h-16 rounded-full bg-[#262626] flex items-center justify-center text-[#72fe8f] group-hover:scale-110 transition-transform duration-300">
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="m16 10-4 4-4-4"/></svg>
                    </div>
                    <div>
                        <p className="text-[0.6875rem] uppercase tracking-wider text-[#adaaaa] font-medium">Vibe Type</p>
                        <span className="inline-block mt-2 px-4 py-1 rounded-full text-[0.6875rem] font-bold text-[#005f26]"
                            style={{ background: 'linear-gradient(135deg, #72fe8f 0%, #1cb853 100%)', boxShadow: '0 5px 15px -3px rgba(114,254,143,0.3)' }}>
                            {profile.vibe_type || 'Eclectic Listener'}
                        </span>
                    </div>
                </div>
            </section>

            {/* Feature Breakdown */}
            <section className="px-12 pb-32 max-w-7xl mx-auto">
                <h3 className="text-xl font-['Plus_Jakarta_Sans'] font-bold text-white mb-12 flex items-center gap-3">
                    <span className="w-8 h-[2px] bg-[#72fe8f]" />
                    Detailed Analysis
                </h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-24 gap-y-10">
                    {LABELS.map((label, i) => (
                        <FeatureBar
                            key={label}
                            label={label}
                            value={features[label.toLowerCase()] || 0}
                            delay={i * 100}
                        />
                    ))}
                </div>
            </section>
        </div>
    );
}
