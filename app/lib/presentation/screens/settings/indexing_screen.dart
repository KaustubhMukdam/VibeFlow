import 'dart:async';
import 'package:flutter/material.dart';
import '../../data/datasources/remote/indexing_api.dart';

class IndexingScreen extends StatefulWidget {
  final List<String> filePaths;
  const IndexingScreen({super.key, required this.filePaths});

  @override
  State<IndexingScreen> createState() => _IndexingScreenState();
}

class _IndexingScreenState extends State<IndexingScreen> {
  final IndexingApiClient _apiClient = IndexingApiClient();
  Timer? _timer;
  int _total = 1;
  int _completed = 0;
  String _currentFile = 'Initializing...';
  bool _isRunning = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _startIndexing();
  }

  Future<void> _startIndexing() async {
    try {
      await _apiClient.startIndexing(widget.filePaths);
      _timer = Timer.periodic(const Duration(seconds: 2), (timer) {
        _checkStatus();
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = "Failed to communicate with ML Backend: $e";
          _isRunning = false;
        });
      }
    }
  }

  Future<void> _checkStatus() async {
    final status = await _apiClient.checkStatus();
    
    if (status['status'] == 'error') {
      if (mounted) {
        setState(() {
          _errorMessage = status['message'];
          _isRunning = false;
        });
        _timer?.cancel();
      }
      return;
    }

    if (mounted) {
      setState(() {
        _total = status['total'] ?? 1;
        _completed = status['completed'] ?? 0;
        _currentFile = status['current_file']?.split(RegExp(r'[/\\]')).last ?? 'Waiting...';
      });

      if (status['status'] == 'idle' && _completed == _total && _total > 0) {
        _timer?.cancel();
        setState(() {
          _isRunning = false;
          _currentFile = "Indexing Complete!";
        });
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final progress = _total > 0 ? (_completed / _total) : 0.0;
    
    return Scaffold(
      backgroundColor: const Color(0xFF0F131C),
      appBar: AppBar(
        title: const Text('Audio Analytics Library'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Icon(Icons.settings_suggest, size: 80, color: Colors.blueAccent),
            const SizedBox(height: 32),
            const Text(
              'Processing Audio Features',
              style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            if (_errorMessage != null)
              Text(
                _errorMessage!,
                style: const TextStyle(color: Colors.redAccent, fontSize: 14),
                textAlign: TextAlign.center,
              )
            else ...[
              Text(
                'Extracting MFCCs, Chroma, Energy & Tempo',
                style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 14),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              LinearProgressIndicator(
                value: progress,
                backgroundColor: Colors.white12,
                color: Colors.cyanAccent,
                minHeight: 8,
                borderRadius: BorderRadius.circular(8),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('$_completed / $_total Indexed', style: const TextStyle(color: Colors.white70)),
                  Text('${(progress * 100).toStringAsFixed(1)}%', style: const TextStyle(color: Colors.white70)),
                ],
              ),
              const SizedBox(height: 24),
              Text(
                _currentFile,
                style: const TextStyle(color: Colors.white54, fontSize: 12),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              if (!_isRunning && _errorMessage == null) ...[
                const SizedBox(height: 32),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent),
                  child: const Text('Return to Library'),
                )
              ]
            ]
          ],
        ),
      ),
    );
  }
}
