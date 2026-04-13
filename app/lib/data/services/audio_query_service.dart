import 'package:on_audio_query/on_audio_query.dart';

class AudioQueryService {
  final OnAudioQuery _audioQuery = OnAudioQuery();

  Future<bool> requestPermissions() async {
    bool permissionStatus = await _audioQuery.permissionsStatus();
    if (!permissionStatus) {
      permissionStatus = await _audioQuery.permissionsRequest();
    }
    return permissionStatus;
  }

  Future<List<SongModel>> fetchDeviceSongs() async {
    final bool hasPermission = await requestPermissions();
    if (!hasPermission) {
      return [];
    }

    return await _audioQuery.querySongs(
      sortType: null,
      orderType: OrderType.ASC_OR_SMALLER,
      uriType: UriType.EXTERNAL,
      ignoreCase: true,
    );
  }
}
