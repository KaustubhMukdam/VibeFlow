import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/song.dart';
import '../../data/repositories/song_repository.dart';

final songRepositoryProvider = Provider<SongRepository>((ref) {
  return SongRepository();
});

final librarySongsProvider = FutureProvider<List<Song>>((ref) async {
  final repository = ref.read(songRepositoryProvider);
  return repository.getAllSongs();
});

final syncLibraryProvider = FutureProvider<void>((ref) async {
  final repository = ref.read(songRepositoryProvider);
  await repository.syncDeviceSongs();
  ref.invalidate(librarySongsProvider);
});
