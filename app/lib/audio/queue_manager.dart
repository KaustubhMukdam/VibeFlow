import 'package:audio_service/audio_service.dart';
import 'package:just_audio/just_audio.dart';
import '../data/models/song.dart';
import 'audio_player_manager.dart';

class QueueManager {
  final AudioPlayerManager _playerManager;
  final BaseAudioHandler _audioHandler;

  QueueManager(this._playerManager, this._audioHandler);

  final List<Song> _queue = [];
  int _currentIndex = -1;

  List<Song> get currentQueue => _queue;
  Song? get currentSong => _currentIndex >= 0 && _currentIndex < _queue.length 
    ? _queue[_currentIndex] 
    : null;

  Future<void> replaceQueue(List<Song> songs, {int initialIndex = 0}) async {
    _queue.clear();
    _queue.addAll(songs);
    
    final audioSources = _queue.map((song) => 
      AudioSource.uri(
        Uri.file(song.filePath),
        tag: MediaItem(
          id: song.id,
          album: song.album,
          title: song.title,
          artist: song.artist,
          duration: Duration(milliseconds: song.durationMs),
          extras: {'url': song.filePath},
        ),
      )
    ).toList();

    final playlist = ConcatenatingAudioSource(
      children: audioSources,
    );

    await _playerManager.setAudioSource(playlist);
    
    // Update audio_service queue
    final mediaItems = _queue.map((song) => MediaItem(
          id: song.id,
          album: song.album,
          title: song.title,
          artist: song.artist,
          duration: Duration(milliseconds: song.durationMs),
    )).toList();
    _audioHandler.queue.add(mediaItems);

    _currentIndex = initialIndex;
    _playerManager.player.seek(Duration.zero, index: initialIndex);
    _playerManager.play();
  }

  void setShuffleMode(bool enabled) {
    _playerManager.player.setShuffleModeEnabled(enabled);
  }

  void setRepeatMode(LoopMode mode) {
    _playerManager.player.setLoopMode(mode);
  }

  void addToQueue(Song song) {
    _queue.add(song);
    // You would update ConcatenatingAudioSource here if tracking dynamically
  }

  void playNext(Song song) {
    if (_currentIndex != -1) {
      _queue.insert(_currentIndex + 1, song);
      // Synchronize JustAudio's ConcatenatingAudioSource instance
    }
  }
}
