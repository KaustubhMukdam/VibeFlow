import 'package:just_audio/just_audio.dart';

class AudioPlayerManager {
  final AudioPlayer _player = AudioPlayer();

  AudioPlayer get player => _player;

  Future<void> play() async {
    await _player.play();
  }

  Future<void> pause() async {
    await _player.pause();
  }

  Future<void> seek(Duration position) async {
    await _player.seek(position);
  }

  Future<void> stop() async {
    await _player.stop();
  }

  Future<void> setAudioSource(AudioSource source) async {
    await _player.setAudioSource(source);
  }

  void dispose() {
    _player.dispose();
  }
}
