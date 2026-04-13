import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'presentation/screens/library/library_screen.dart';

class VibeFlowApp extends ConsumerWidget {
  const VibeFlowApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'VibeFlow',
      theme: AppTheme.darkTheme,
      home: const LibraryScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

