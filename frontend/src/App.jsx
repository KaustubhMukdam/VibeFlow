import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { Home as HomeIcon, Zap, BarChart2, Radar, Clock, Settings, User } from 'lucide-react';
import Home from './pages/Home';
import WeekendVibe from './pages/WeekendVibe';
import LibraryIntel from './pages/LibraryIntel';
import TasteProfile from './pages/TasteProfile';
import ListeningHistory from './pages/ListeningHistory';

const NAV_ITEMS = [
    { to: '/', icon: HomeIcon, label: 'Home' },
    { to: '/weekend', icon: Zap, label: 'Weekend Vibe' },
    { to: '/intel', icon: BarChart2, label: 'Library Intel' },
    { to: '/taste', icon: Radar, label: 'Taste Profile' },
    { to: '/history', icon: Clock, label: 'History' },
];

function App() {
    return (
        <Router>
            <div className="flex h-screen bg-[#121212] text-white font-sans overflow-hidden">

                {/* Sidebar */}
                <aside className="w-64 bg-black flex flex-col justify-between flex-shrink-0">
                    <div>
                        <div className="p-6">
                            <h1 className="text-2xl font-bold text-green-500 tracking-tight">VibeFlow</h1>
                        </div>
                        <nav className="mt-6 flex flex-col gap-2 px-4">
                            {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
                                <NavLink
                                    key={to}
                                    to={to}
                                    end={to === '/'}
                                    className={({ isActive }) =>
                                        `flex items-center gap-4 px-4 py-3 rounded-lg transition-colors ${
                                            isActive
                                                ? 'bg-neutral-800 text-white border-l-4 border-green-500'
                                                : 'text-gray-400 hover:text-white hover:bg-neutral-900'
                                        }`
                                    }
                                >
                                    <Icon size={20} />
                                    <span className="font-semibold">{label}</span>
                                </NavLink>
                            ))}
                        </nav>
                    </div>

                    <div className="p-6 text-gray-500 flex justify-between">
                        <Settings className="hover:text-white cursor-pointer transition-colors" />
                        <User className="hover:text-white cursor-pointer transition-colors" />
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 overflow-y-auto bg-gradient-to-b from-[#1e1e1e] to-[#121212]">
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/weekend" element={<WeekendVibe />} />
                        <Route path="/intel" element={<LibraryIntel />} />
                        <Route path="/taste" element={<TasteProfile />} />
                        <Route path="/history" element={<ListeningHistory />} />
                    </Routes>
                </main>

            </div>
        </Router>
    );
}

export default App;