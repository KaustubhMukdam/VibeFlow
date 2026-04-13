import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DatabaseHelper {
  static const String dbName = 'vibeflow.db';
  static const int dbVersion = 1;

  static Database? _database;

  static Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB();
    return _database!;
  }

  static Future<Database> _initDB() async {
    String path = join(await getDatabasesPath(), dbName);
    
    return await openDatabase(
      path,
      version: dbVersion,
      onCreate: _onCreate,
    );
  }

  static Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE songs (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          artist TEXT,
          album TEXT,
          file_path TEXT NOT NULL UNIQUE,
          duration_ms INTEGER,
          genre_tag TEXT,
          indexed_at DATETIME,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    ''');

    await db.execute('''
      CREATE TABLE behavior_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          song_id TEXT REFERENCES songs(id),
          event_type TEXT NOT NULL,
          skip_position_pct REAL,
          session_id TEXT NOT NULL,
          timestamp DATETIME NOT NULL
      )
    ''');
    
    // More tables (playlists, etc.) can be added here or in migrations.
    await db.execute('''
      CREATE TABLE playlists (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          type TEXT NOT NULL,
          created_at DATETIME,
          metadata TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE playlist_songs (
          playlist_id TEXT REFERENCES playlists(id),
          song_id TEXT REFERENCES songs(id),
          position INTEGER,
          PRIMARY KEY (playlist_id, song_id)
      )
    ''');
  }
}
