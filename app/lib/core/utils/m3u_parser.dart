import 'dart:io';

class M3uParser {
  /// Parses an .m3u file and returns a list of file paths.
  /// Handles both relative and absolute paths by resolving relative paths
  /// against the directory of the .m3u file.
  static Future<List<String>> parseFile(String filePath) async {
    final file = File(filePath);
    if (!await file.exists()) {
      throw Exception('M3U file not found');
    }

    final lines = await file.readAsLines();
    final List<String> extractedPaths = [];
    final baseDir = file.parent.path;

    for (var line in lines) {
      line = line.trim();
      // Skip comments or empty lines
      if (line.isEmpty || line.startsWith('#')) {
        continue;
      }

      // Check if it's an absolute path
      if (line.startsWith('/') ||
          line.startsWith(RegExp(r'^[a-zA-Z]:\\')) ||
          line.startsWith('content://')) {
        extractedPaths.add(line);
      } else {
        // It's a relative path, resolve it against baseDir
        final resolvedPath = '$baseDir${Platform.pathSeparator}$line';
        extractedPaths.add(resolvedPath);
      }
    }

    return extractedPaths;
  }
}
