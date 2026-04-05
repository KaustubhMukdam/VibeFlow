import React, { useState, useEffect } from 'react';
import { getListeningHistory, getRecentSessions } from '../api';

// ── Heatmap Cell ────────────────────────────────────────────────────────────
function HeatmapCell({ value, maxVal }) {
    const intensity = maxVal > 0 ? value / maxVal : 0;
    let bg;
    if (intensity === 0) bg = '#0e0e0e';
    else if (intensity < 0.25) bg = 'rgba(28, 184, 83, 0.3)';
    else if (intensity < 0.5) bg = 'rgba(28, 184, 83, 0.6)';
    else if (intensity < 0.75) bg = '#1cb853';
    else bg = '#72fe8f';

    return (
        <div
            className="w-full h-4 rounded-sm transition-colors duration-300"
            style={{ backgroundColor: bg }}
            title={`${value} plays`}
        />
    );
}

// ── Activity Heatmap ────────────────────────────────────────────────────────
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function ActivityHeatmap({ grid, maxPlays }) {
    return (
        <div className="bg-[#1a1a1a] p-10 rounded-2xl">
            <div className="flex justify-between items-end mb-10">
                <h2 className="text-2xl font-bold font-['Plus_Jakarta_Sans']">Activity Heatmap</h2>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] text-[#adaaaa] uppercase font-bold">Less</span>
                    <div className="flex gap-1">
                        <div className="w-3 h-3 rounded-sm bg-[#0e0e0e]" />
                        <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'rgba(28,184,83,0.5)' }} />
                        <div className="w-3 h-3 rounded-sm bg-[#1cb853]" />
                        <div className="w-3 h-3 rounded-sm bg-[#72fe8f]" />
                    </div>
                    <span className="text-[10px] text-[#adaaaa] uppercase font-bold">More</span>
                </div>
            </div>

            <div className="overflow-x-auto">
                <div className="min-w-[700px]">
                    {/* Hour labels */}
                    <div className="grid grid-cols-[50px_1fr] gap-4 mb-2">
                        <div />
                        <div className="grid grid-cols-24 gap-1">
                            {[0, 6, 12, 18].map(h => (
                                <span key={h} className="text-[8px] text-[#adaaaa] font-bold"
                                    style={{ gridColumn: h + 1 }}>
                                    {h === 0 ? '12AM' : h === 6 ? '6AM' : h === 12 ? '12PM' : '6PM'}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Day rows */}
                    {DAYS.map((day, di) => (
                        <div key={day} className="grid grid-cols-[50px_1fr] gap-4 mb-1">
                            <span className="text-[10px] text-[#adaaaa] font-bold flex items-center">{day}</span>
                            <div className="grid grid-cols-24 gap-1">
                                {HOURS.map(h => (
                                    <HeatmapCell
                                        key={h}
                                        value={grid[di]?.[h] || 0}
                                        maxVal={maxPlays}
                                    />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ── Session Card ────────────────────────────────────────────────────────────
function SessionCard({ session, isFirst }) {
    const [expanded, setExpanded] = useState(isFirst);

    const startDate = session.started_at ? new Date(session.started_at) : null;
    const dateStr = startDate
        ? startDate.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
        : 'Unknown';

    // Calculate duration
    let durationStr = '—';
    if (session.started_at && session.ended_at) {
        const ms = new Date(session.ended_at) - new Date(session.started_at);
        const mins = Math.round(ms / 60000);
        durationStr = mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m`;
    }

    const skipRate = session.skip_rate != null ? Math.round(session.skip_rate * 100) : 0;

    return (
        <div className={`${expanded ? 'bg-[#262626]' : 'bg-[#1a1a1a] hover:bg-[#2c2c2c]'} rounded-2xl overflow-hidden transition-all duration-300`}>
            <div
                className="p-6 flex flex-wrap items-center justify-between gap-4 cursor-pointer"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-6">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${expanded ? 'bg-[#72fe8f]/20' : 'bg-white/5'}`}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
                            stroke={expanded ? '#72fe8f' : '#adaaaa'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="m9 18 6-6-6-6"/></svg>
                    </div>
                    <div>
                        <h3 className="font-bold text-lg">{dateStr}</h3>
                        <p className="text-xs text-[#adaaaa] uppercase tracking-widest font-bold">Session Overview</p>
                    </div>
                </div>

                <div className="flex gap-8 text-sm">
                    <div className="flex flex-col">
                        <span className="text-[#adaaaa] text-[10px] uppercase font-bold">Duration</span>
                        <span>{durationStr}</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[#adaaaa] text-[10px] uppercase font-bold">Songs</span>
                        <span>{session.song_count || session.tracks?.length || 0} songs</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[#adaaaa] text-[10px] uppercase font-bold">Skip Rate</span>
                        <span className={`font-bold ${skipRate > 30 ? 'text-[#ff7351]' : 'text-[#72fe8f]'}`}>
                            {skipRate}%
                        </span>
                    </div>
                </div>

                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
                    stroke="#adaaaa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    className={`transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}>
                    <path d="m6 9 6 6 6-6"/></svg>
            </div>

            {/* Expanded tracklist */}
            {expanded && session.tracks && session.tracks.length > 0 && (
                <div className="px-6 pb-6 pt-2">
                    <div className="bg-[#1a1a1a] rounded-2xl p-4">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="text-[#adaaaa] text-[10px] uppercase tracking-widest font-bold border-b border-white/5">
                                    <th className="py-3 px-2">#</th>
                                    <th className="py-3 px-2">Title</th>
                                    <th className="py-3 px-2">Artist</th>
                                    <th className="py-3 px-2">Duration</th>
                                    <th className="py-3 px-2">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {session.tracks.map((track, i) => {
                                    const durSec = track.play_duration_ms
                                        ? Math.round(track.play_duration_ms / 1000)
                                        : 0;
                                    const durStr = `${Math.floor(durSec / 60)}:${String(durSec % 60).padStart(2, '0')}`;
                                    return (
                                        <tr key={i} className="hover:bg-white/5 transition-colors">
                                            <td className="py-3 px-2 text-[#adaaaa]">{String(i + 1).padStart(2, '0')}</td>
                                            <td className="py-3 px-2 font-medium">{track.title || track.song_id}</td>
                                            <td className="py-3 px-2 text-[#adaaaa]">{track.artist || '—'}</td>
                                            <td className="py-3 px-2 text-[#adaaaa]">{durStr}</td>
                                            <td className="py-3 px-2">
                                                <div className={`w-2 h-2 rounded-full ${track.skipped ? 'bg-[#ff7351]' : 'bg-[#72fe8f]'}`} />
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Main Component ─────────────────────────────────────────────────────────
export default function ListeningHistory() {
    const [historyData, setHistoryData] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            try {
                const [histRes, sessRes] = await Promise.all([
                    getListeningHistory(50),
                    getRecentSessions(10),
                ]);
                setHistoryData(histRes.data);
                setSessions(sessRes.data.sessions || []);
            } catch (err) {
                console.error('Failed to load history:', err);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    if (loading) {
        return (
            <div className="p-12 flex items-center justify-center min-h-screen">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-2 border-[#72fe8f] border-t-transparent rounded-full animate-spin" />
                    <p className="text-[#adaaaa] text-sm">Loading history...</p>
                </div>
            </div>
        );
    }

    const stats = historyData?.stats || {};
    const heatmap = historyData?.heatmap || { grid: Array(7).fill(Array(24).fill(0)), max_plays: 0 };
    const recentPlays = historyData?.recent_plays || [];

    return (
        <div className="min-h-screen pb-24 lg:pb-12">
            {/* Header */}
            <header className="px-8 lg:px-16 pt-20 pb-12">
                <h1 className="text-[3.5rem] font-['Plus_Jakarta_Sans'] font-extrabold tracking-[-0.04em] leading-tight text-white">
                    Listening History
                </h1>
                <p className="text-[#adaaaa] text-lg mt-2" style={{ fontFamily: 'Inter, sans-serif' }}>
                    Your musical journey, tracked and analyzed
                </p>
            </header>

            {/* Stats Row */}
            <section className="px-8 lg:px-16 mb-16">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {/* Total Plays */}
                    <div className="bg-[#1a1a1a] p-8 rounded-2xl flex flex-col gap-4">
                        <div className="flex justify-between items-start">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#72fe8f" stroke="none">
                                <polygon points="5,3 19,12 5,21" /></svg>
                            <span className="text-[10px] uppercase tracking-widest text-[#adaaaa] font-bold">Total Plays</span>
                        </div>
                        <div className="text-3xl font-['Plus_Jakarta_Sans'] font-bold">
                            {stats.total_plays?.toLocaleString() || '0'}
                        </div>
                    </div>

                    {/* Skip Rate */}
                    <div className="bg-[#1a1a1a] p-8 rounded-2xl flex flex-col gap-4">
                        <div className="flex justify-between items-start">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
                                stroke={stats.skip_rate > 30 ? '#ff7351' : '#72fe8f'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="m12 2 3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.27 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>
                            <span className="text-[10px] uppercase tracking-widest text-[#adaaaa] font-bold">Skip Rate</span>
                        </div>
                        <div className={`text-3xl font-['Plus_Jakarta_Sans'] font-bold ${stats.skip_rate > 30 ? 'text-[#ff7351]' : 'text-[#72fe8f]'}`}>
                            {stats.skip_rate || 0}%
                        </div>
                    </div>

                    {/* Most Played Genre */}
                    <div className="bg-[#1a1a1a] p-8 rounded-2xl flex flex-col gap-4">
                        <div className="flex justify-between items-start">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
                                stroke="#72fe8f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                            <span className="text-[10px] uppercase tracking-widest text-[#adaaaa] font-bold">Most Played</span>
                        </div>
                        <div>
                            <span className="inline-block px-3 py-1 bg-[#1cb853] text-[#002a0c] rounded-full text-sm font-bold">
                                {stats.most_played_genre || 'N/A'}
                            </span>
                        </div>
                    </div>

                    {/* Avg Session */}
                    <div className="bg-[#1a1a1a] p-8 rounded-2xl flex flex-col gap-4">
                        <div className="flex justify-between items-start">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
                                stroke="#72fe8f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/></svg>
                            <span className="text-[10px] uppercase tracking-widest text-[#adaaaa] font-bold">Avg Session</span>
                        </div>
                        <div className="text-3xl font-['Plus_Jakarta_Sans'] font-bold">
                            {stats.avg_session_length || 0} songs
                        </div>
                    </div>
                </div>
            </section>

            {/* Heatmap */}
            <section className="px-8 lg:px-16 mb-16">
                <ActivityHeatmap grid={heatmap.grid} maxPlays={heatmap.max_plays} />
            </section>

            {/* Recent Sessions */}
            {sessions.length > 0 && (
                <section className="px-8 lg:px-16 mb-16">
                    <h2 className="text-2xl font-bold font-['Plus_Jakarta_Sans'] mb-6">Recent Sessions</h2>
                    <div className="flex flex-col gap-4">
                        {sessions.map((s, i) => (
                            <SessionCard key={s.session_id} session={s} isFirst={i === 0} />
                        ))}
                    </div>
                </section>
            )}

            {/* Recent Plays Table */}
            {recentPlays.length > 0 && (
                <section className="px-8 lg:px-16 mb-16">
                    <h2 className="text-2xl font-bold font-['Plus_Jakarta_Sans'] mb-6">Recent Plays</h2>
                    <div className="bg-[#1a1a1a] p-4 rounded-2xl">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-separate border-spacing-y-2">
                                <thead>
                                    <tr className="text-[10px] text-[#adaaaa] uppercase tracking-widest font-bold">
                                        <th className="px-4 py-2">Time</th>
                                        <th className="px-4 py-2">Song</th>
                                        <th className="px-4 py-2">Artist</th>
                                        <th className="px-4 py-2">Genre</th>
                                        <th className="px-4 py-2">Duration</th>
                                        <th className="px-4 py-2">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recentPlays.map((play, i) => {
                                        const time = play.played_at
                                            ? new Date(play.played_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
                                            : '—';
                                        const durSec = play.play_duration_ms ? Math.round(play.play_duration_ms / 1000) : 0;
                                        const durStr = `${Math.floor(durSec / 60)}:${String(durSec % 60).padStart(2, '0')}`;

                                        return (
                                            <tr key={i}
                                                className={`${i % 2 === 0 ? 'bg-[#0e0e0e]/40' : 'bg-[#131313]/40'} hover:bg-[#2c2c2c] transition-colors rounded-lg`}>
                                                <td className="px-4 py-4 text-xs font-mono text-[#adaaaa]">{time}</td>
                                                <td className="px-4 py-4 font-bold">{play.title || play.song_id}</td>
                                                <td className="px-4 py-4 text-[#adaaaa]">{play.artist || '—'}</td>
                                                <td className="px-4 py-4">
                                                    {play.genre && (
                                                        <span className="px-2 py-1 bg-[#262626] text-[10px] font-bold rounded text-white uppercase">
                                                            {play.genre}
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-4 text-[#adaaaa]">{durStr}</td>
                                                <td className="px-4 py-4">
                                                    {play.skipped ? (
                                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                                                            stroke="#ff7351" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                            <polygon points="5,4 15,12 5,20"/><line x1="19" y1="5" x2="19" y2="19"/></svg>
                                                    ) : (
                                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                                                            stroke="#72fe8f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                            <path d="M20 6 9 17l-5-5"/></svg>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>
            )}
        </div>
    );
}
