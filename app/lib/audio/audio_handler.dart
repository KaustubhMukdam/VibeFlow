import 'package:audio_service/audio_service.dart';
import 'package:just_audio/just_audio.dart';
import 'audio_player_manager.dart';
import '../data/models/song.dart';

class AppAudioHandler extends BaseAudioHandler with SeekHandler {
  final AudioPlayerManager _playerManager;

  AppAudioHandler(this._playerManager) {
    _listenToPlaybackState();
    _listenToPosition();
  }

  void _listenToPlaybackState() {
    _playerManager.player.playbackEventStream.listen((PlaybackEvent event) {
      final playing = _playerManager.player.playing;
      playbackState.add(playbackState.value.copyWith(
        controls: [
          MediaControl.skipToPrevious,
          if (playing) MediaControl.pause else MediaControl.play,
          MediaControl.stop,
          MediaControl.skipToNext,
        ],
        systemActions: const {
          MediaAction.seek,
          MediaAction.seekForward,
          MediaAction.seekBackward,
        },
        androidCompactActionIndices: const [0, 1, 3],
        processingState: const {
          ProcessingState.idle: AudioProcessingState.idle,
          ProcessingState.loading: AudioProcessingState.loading,
          ProcessingState.buffering: AudioProcessingState.buffering,
          ProcessingState.ready: AudioProcessingState.ready,
          ProcessingState.completed: AudioProcessingState.completed,
        }[_playerManager.player.processingState]!,
        playing: playing,
        updatePosition: _playerManager.player.position,
        bufferedPosition: _playerManager.player.bufferedPosition,
        speed: _playerManager.player.speed,
        queueIndex: event.currentIndex,
      ));
    });
  }

  void _listenToPosition() {
    // Optionally listen to position to sync UI/states, handled by audio_service internally via event stream above
  }

  @override
  Future<void> play() => _playerManager.play();

  @override
  Future<void> pause() => _playerManager.pause();

  @override
  Future<void> seek(Duration position) => _playerManager.seek(position);

  @override
  Future<void> stop() async {
    await _playerManager.stop();
    return super.stop();
  }

  /// Custom method to play a specific song
  Future<void> playSong(Song song) async {
    final mediaItem = MediaItem(
      id: song.id,
      album: song.album,
      title: song.title,
      artist: song.artist,
      duration: Duration(milliseconds: song.durationMs),
      extras: {'url': song.filePath},
    );
    
    mediaItem.add(mediaItem);
    
    await _playerManager.setAudioSource(AudioSource.uri(Uri.file(song.filePath)));
    await _playerManager.play();
  }
}
