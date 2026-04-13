import 'package:sqflite/sqflite.dart';
import '../models/song.dart';
import '../services/audio_query_service.dart';
import '../datasources/local/db_helper.dart';

class SongRepository {
  final AudioQueryService _audioQueryService = AudioQueryService();

  Future<void> syncDeviceSongs() async {
    final deviceSongs = await _audioQueryService.fetchDeviceSongs();
    final db = await DatabaseHelper.database;
    
    final batch = db.batch();
    for (var dSong in deviceSongs) {
      if (dSong.data == null) continue; // Skip if no file path
      
      final song = Song(
        id: dSong.id.toString(),
        title: dSong.title,
        artist: dSong.artist ?? 'Unknown Artist',
        album: dSong.album ?? 'Unknown Album',
        filePath: dSong.data,
        durationMs: dSong.duration ?? 0,
      );
      
      batch.insert(
        'songs',
        song.toMap(),
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
    }
    await batch.commit(noResult: true);
  }

  Future<List<Song>> getAllSongs() async {
    final db = await DatabaseHelper.database;
    final List<Map<String, dynamic>> maps = await db.query('songs');
    return List.generate(maps.length, (i) => Song.fromMap(maps[i]));
  }

  Future<List<Song>> searchSongs(String query) async {
    final db = await DatabaseHelper.database;
    final List<Map<String, dynamic>> maps = await db.query(
      'songs',
      where: 'title LIKE ? OR artist LIKE ? OR album LIKE ?',
      whereArgs: ['%$query%', '%$query%', '%$query%'],
    );
    return List.generate(maps.length, (i) => Song.fromMap(maps[i]));
  }
}
