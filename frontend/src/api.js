import axios from 'axios';

const API_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
});

// Recommendations
export const getDailyRecommendation = () => api.get('/recommend/daily');
export const getTopRecommendations = (limit = 5) => api.get(`/recommend/top?n=${limit}`);
export const getWeekendPlaylist = () => api.get('/recommend/weekend');

// Sessions
export const startSession = () => api.post('/session/start');
export const logTrackPlay = (sessionId, payload) => api.post(`/session/${sessionId}/track`, payload);
export const endSession = (sessionId) => api.post(`/session/${sessionId}/end`);
export const getNextSongs = (sessionId, count = 3) => api.get(`/session/${sessionId}/next?count=${count}`);
export const getRecentSessions = (limit = 10) => api.get(`/session/?limit=${limit}`);

// Library Intel
export const getLibraryStats = () => api.get('/library/stats');
export const getGenreDistribution = () => api.get('/library/genres');

// Taste Profile
export const getTasteProfile = () => api.get('/library/taste-profile');

// Listening History
export const getListeningHistory = (limit = 50) => api.get(`/library/history?limit=${limit}`);

export default api;
