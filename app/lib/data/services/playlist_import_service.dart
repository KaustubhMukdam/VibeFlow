import 'package:uuid/uuid.dart';
import '../../core/utils/m3u_parser.dart';
import '../datasources/local/db_helper.dart';

class PlaylistImportService {
  final _uuid = const Uuid();

  /// Import an m3u file into the database. Returns the new playlist ID.
  Future<String> importM3u(String name, String m3uFilePath) async {
    final paths = await M3uParser.parseFile(m3uFilePath);
    
    final db = await DatabaseHelper.database;
    final playlistId = _uuid.v4();

    await db.transaction((txn) async {
      // Create playlist entry
      await txn.insert('playlists', {
        'id': playlistId,
        'name': name,
        'type': 'manual',
        'created_at': DateTime.now().toIso8601String(),
        'metadata': '{}',
      });

      // Map paths to song_id if song exists in our DB
      // We do a query to find song_ids
      int position = 0;
      for (final path in paths) {
        final result = await txn.query(
          'songs',
          columns: ['id'],
          where: 'file_path = ?',
          whereArgs: [path],
          limit: 1,
        );
        
        if (result.isNotEmpty) {
          final songId = result.first['id'] as String;
          await txn.insert('playlist_songs', {
            'playlist_id': playlistId,
            'song_id': songId,
            'position': position,
          });
          position++;
        }
      }
    });

    return playlistId;
  }
}
