import React, { useState, useEffect } from 'react';
import { Database, Sparkles, Folder, BrainCircuit } from 'lucide-react';
import { getLibraryStats, getGenreDistribution } from '../api';

export default function LibraryIntel() {
    const [stats, setStats] = useState(null);
    const [genres, setGenres] = useState(null);

    useEffect(() => {
        async function loadData() {
            try {
                const [statsRes, genreRes] = await Promise.all([
                    getLibraryStats(),
                    getGenreDistribution()
                ]);
                setStats(statsRes.data);
                setGenres(genreRes.data);
            } catch (err) {
                console.error(err);
            }
        }
        loadData();
    }, []);

    if (!stats) return <div className="p-8">Loading...</div>;

    return (
        <div className="p-8">
            <div className="mb-10">
                <h1 className="text-4xl font-black mb-2">Library Intel</h1>
                <p className="text-gray-400 text-lg">Predictive analytics for your {stats.total_songs} tracked melodies.</p>
            </div>

            {/* Top KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-neutral-800/50 p-6 rounded-2xl border border-neutral-700">
                    <Database className="text-gray-400 mb-4" size={28} />
                    <p className="text-sm text-gray-400 font-semibold tracking-wide mb-1">TOTAL SONGS</p>
                    <p className="text-4xl font-bold text-white">{stats.total_songs}</p>
                </div>
                <div className="bg-green-500 p-6 rounded-2xl shadow-[0_0_30px_rgba(34,197,94,0.3)]">
                    <Sparkles className="text-green-900 mb-4" size={28} />
                    <p className="text-sm text-green-900 font-bold tracking-wide mb-1">AI TAGGED SONGS</p>
                    <p className="text-4xl font-black text-black">{stats.tagged_songs}</p>
                </div>
                <div className="bg-neutral-800/50 p-6 rounded-2xl border border-neutral-700">
                    <Folder className="text-gray-400 mb-4" size={28} />
                    <p className="text-sm text-gray-400 font-semibold tracking-wide mb-1">TOTAL PLAYLISTS</p>
                    <p className="text-4xl font-bold text-white">{stats.total_playlists}</p>
                </div>
            </div>

            {/* Genre Distribution */}
            {genres && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-2 bg-neutral-800/50 p-8 rounded-2xl border border-neutral-700">
                        <h2 className="text-xl font-bold mb-6">Genre Distribution</h2>
                        <div className="space-y-5">
                            {genres.genres.map((g) => (
                                <div key={g.genre}>
                                    <div className="flex justify-between text-sm mb-2">
                                        <span className="text-gray-300 font-medium">{g.genre}</span>
                                        <span className="text-gray-400">{g.percentage}%</span>
                                    </div>
                                    <div className="w-full bg-neutral-700 rounded-full h-2">
                                        <div className="bg-green-400 h-2 rounded-full" style={{ width: `${g.percentage}%` }}></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-neutral-800/50 p-8 rounded-2xl border border-neutral-700 flex flex-col items-center justify-center text-center">
                        <div className="w-24 h-24 rounded-full border-4 border-green-500/30 flex items-center justify-center mb-6 relative">
                            <div className="absolute inset-0 rounded-full border-t-4 border-green-400 animate-spin" style={{ animationDuration: '3s' }}></div>
                            <BrainCircuit className="text-green-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">ML Precision</h3>
                        <p className="text-gray-400 text-sm">Your library is deeply tagged for the mood-based recommendation engine.</p>
                    </div>
                </div>
            )}
        </div>
    );
}