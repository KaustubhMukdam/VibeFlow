import React, { useState, useEffect } from 'react';
import { Play, SkipForward, MoreHorizontal } from 'lucide-react';
import { getDailyRecommendation, getTopRecommendations, startSession, logTrackPlay } from '../api';

export default function Home() {
    const [dailyPick, setDailyPick] = useState(null);
    const [topRecs, setTopRecs] = useState([]);
    const [sessionId, setSessionId] = useState(null);

    useEffect(() => {
        async function loadData() {
            try {
                const [dailyRes, topRes, sessionRes] = await Promise.all([
                    getDailyRecommendation(),
                    getTopRecommendations(5),
                    startSession()
                ]);
                setDailyPick(dailyRes.data);
                setTopRecs(topRes.data.recommendations || []);
                setSessionId(sessionRes.data.session_id);
            } catch (err) {
                console.error(err);
            }
        }
        loadData();
    }, []);

    const handleAction = async (actionType) => {
        if (!dailyPick || !sessionId) return;
        const isSkip = actionType === 'skip';
        await logTrackPlay(sessionId, {
            song_id: dailyPick.song_id,
            play_duration_ms: isSkip ? 10000 : 180000,
            song_duration_ms: 200000,
            skipped: isSkip,
            skip_time_ms: isSkip ? 10000 : null
        });
        alert(`Track ${isSkip ? 'Skipped' : 'Played'}! Bandit updated.`);
    };

    return (
        <div className="p-8">
            {/* Hero Section */}
            {dailyPick && (
                <div className="relative rounded-3xl p-10 overflow-hidden shadow-2xl bg-gradient-to-r from-emerald-900 to-teal-900">
                    <div className="relative z-10">
                        <span className="bg-black/40 text-green-400 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">Today's Pick</span>
                        <h1 className="text-6xl font-black text-white mt-4 mb-2">{dailyPick.title}</h1>
                        <p className="text-xl text-gray-300">{dailyPick.artist} • {dailyPick.genre}</p>

                        <div className="flex gap-4 mt-8">
                            <button onClick={() => handleAction('play')} className="bg-green-500 hover:bg-green-400 text-black font-bold py-3 px-8 rounded-full flex items-center gap-2 transition-transform hover:scale-105">
                                <Play fill="currentColor" size={20} /> Play
                            </button>
                            <button onClick={() => handleAction('skip')} className="bg-black/50 hover:bg-black/70 text-white font-bold py-3 px-8 rounded-full flex items-center gap-2 transition-colors border border-gray-600">
                                <SkipForward size={20} /> Skip
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Top Recommendations */}
            <div className="mt-12">
                <h2 className="text-2xl font-bold mb-1">Top Recommendations</h2>
                <p className="text-gray-400 mb-6">Based on your recent vibe</p>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
                    {topRecs.map((rec, i) => (
                        <div key={rec.song_id} className="bg-neutral-800/50 hover:bg-neutral-800 p-4 rounded-xl transition-colors group cursor-pointer">
                            <div className="w-full aspect-square bg-gradient-to-br from-gray-700 to-gray-900 rounded-lg mb-4 shadow-lg flex items-center justify-center relative">
                                <Play className="opacity-0 group-hover:opacity-100 transition-opacity absolute text-green-500" fill="currentColor" size={40} />
                            </div>
                            <h3 className="font-bold text-white truncate">{rec.title}</h3>
                            <p className="text-sm text-gray-400 truncate">{rec.artist}</p>
                            <div className="flex justify-between items-center mt-3">
                                <span className="text-xs text-green-400 font-semibold">{Math.round(rec.score * 100)}% Match</span>
                                <MoreHorizontal size={16} className="text-gray-500" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}