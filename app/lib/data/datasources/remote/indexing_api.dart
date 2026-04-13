import 'package:dio/dio.dart';

class IndexingApiClient {
  final Dio _dio;

  // Assume running on android emulator points to host localhost via 10.0.2.2 
  // or on desktop directly to localhost.
  final String _baseUrl = 'http://127.0.0.1:8000/api/v1';

  IndexingApiClient() : _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 5),
    receiveTimeout: const Duration(seconds: 5),
  ));

  Future<void> startIndexing(List<String> filePaths) async {
    try {
      await _dio.post('$_baseUrl/index/start', data: {
        'file_paths': filePaths,
      });
    } on DioException catch (e) {
      if (e.response?.statusCode != 400) {
        // 400 usually implies "already running", which is fine to ignore.
        rethrow;
      }
    }
  }

  Future<Map<String, dynamic>> checkStatus() async {
    try {
      final response = await _dio.get('$_baseUrl/index/status');
      return response.data;
    } catch (e) {
      return {
        'status': 'error',
        'message': e.toString(),
      };
    }
  }
}
