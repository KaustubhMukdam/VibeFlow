import React, { useState, useEffect } from 'react';
import { Play, Clock } from 'lucide-react';
import { getWeekendPlaylist } from '../api';

export default function WeekendVibe() {
    const [playlist, setPlaylist] = useState([]);

    useEffect(() => {
        async function load() {
            try {
                const res = await getWeekendPlaylist();
                setPlaylist(res.data.playlist || []);
            } catch (err) {
                console.error(err);
            }
        }
        load();
    }, []);

    return (
        <div className="min-h-full bg-gradient-to-b from-indigo-900 via-[#121212] to-[#121212]">

            {/* Header Banner */}
            <div className="px-8 pt-16 pb-8 flex items-end gap-6">
                <div className="w-52 h-52 shadow-2xl rounded-lg bg-gradient-to-br from-pink-500 to-orange-400 flex items-center justify-center flex-shrink-0">
                    <span className="text-4xl font-black text-white mix-blend-overlay">VIBE</span>
                </div>
                <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-white/80 mb-2">Public Playlist</p>
                    <h1 className="text-7xl font-black text-white mb-6">Weekend Vibe</h1>
                    <p className="text-gray-300 text-sm font-medium">
                        <span className="text-green-400">VibeFlow Curators</span> • {playlist.length} songs
                    </p>
                </div>
            </div>

            <div className="px-8 pb-12">
                <button className="bg-green-500 hover:bg-green-400 text-black rounded-full p-4 transition-transform hover:scale-105 mb-8 shadow-xl">
                    <Play fill="currentColor" size={28} />
                </button>

                {/* Table Header */}
                <div className="grid grid-cols-[50px_2fr_1fr_1fr_50px] text-gray-400 text-xs tracking-wider border-b border-white/10 pb-2 mb-4 px-4">
                    <div>#</div>
                    <div>TITLE</div>
                    <div>ARTIST</div>
                    <div>GENRE</div>
                    <div className="flex justify-end"><Clock size={16} /></div>
                </div>

                {/* Tracks */}
                <div className="flex flex-col">
                    {playlist.map((track, idx) => (
                        <div key={track.song_id} className="grid grid-cols-[50px_2fr_1fr_1fr_50px] items-center text-sm py-3 px-4 hover:bg-white/10 rounded-md transition-colors group cursor-pointer">
                            <div className="text-gray-400 group-hover:hidden">{idx + 1}</div>
                            <div className="hidden group-hover:block text-white"><Play fill="currentColor" size={14} /></div>
                            <div className="font-bold text-white pr-4 truncate">{track.title}</div>
                            <div className="text-gray-400 pr-4 truncate">{track.artist}</div>
                            <div>
                                <span className="border border-gray-600 text-gray-300 text-[10px] px-2 py-1 rounded uppercase tracking-wider">{track.genre}</span>
                            </div>
                            <div className="text-gray-400 text-right">3:42</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}