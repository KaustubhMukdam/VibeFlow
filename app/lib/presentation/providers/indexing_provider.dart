import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/remote/indexing_api.dart';

final indexingApiClientProvider = Provider<IndexingApiClient>((ref) {
  return IndexingApiClient();
});

final indexingTriggerProvider = FutureProvider.family<void, List<String>>((ref, filePaths) async {
  final client = ref.read(indexingApiClientProvider);
  await client.startIndexing(filePaths);
});
