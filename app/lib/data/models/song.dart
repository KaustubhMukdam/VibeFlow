class Song {
  final String id;
  final String title;
  final String artist;
  final String album;
  final String filePath;
  final int durationMs;
  final String? genreTag;
  final DateTime? indexedAt;
  final DateTime? createdAt;

  Song({
    required this.id,
    required this.title,
    required this.artist,
    required this.album,
    required this.filePath,
    required this.durationMs,
    this.genreTag,
    this.indexedAt,
    this.createdAt,
  });

  factory Song.fromMap(Map<String, dynamic> map) {
    return Song(
      id: map['id']?.toString() ?? '',
      title: map['title'] ?? 'Unknown Title',
      artist: map['artist'] ?? 'Unknown Artist',
      album: map['album'] ?? 'Unknown Album',
      filePath: map['file_path'] ?? '',
      durationMs: map['duration_ms'] ?? 0,
      genreTag: map['genre_tag'],
      indexedAt: map['indexed_at'] != null ? DateTime.tryParse(map['indexed_at']) : null,
      createdAt: map['created_at'] != null ? DateTime.tryParse(map['created_at']) : null,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'title': title,
      'artist': artist,
      'album': album,
      'file_path': filePath,
      'duration_ms': durationMs,
      // Optional fields might be updated outside or let them be null if not set
      if (genreTag != null) 'genre_tag': genreTag,
      if (indexedAt != null) 'indexed_at': indexedAt!.toIso8601String(),
    };
  }

  Song copyWith({
    String? title,
    String? artist,
    String? album,
    String? filePath,
    int? durationMs,
    String? genreTag,
    DateTime? indexedAt,
  }) {
    return Song(
      id: this.id,
      title: title ?? this.title,
      artist: artist ?? this.artist,
      album: album ?? this.album,
      filePath: filePath ?? this.filePath,
      durationMs: durationMs ?? this.durationMs,
      genreTag: genreTag ?? this.genreTag,
      indexedAt: indexedAt ?? this.indexedAt,
      createdAt: this.createdAt,
    );
  }
}
