import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/library_provider.dart';

class LibraryScreen extends ConsumerWidget {
  const LibraryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final songsAsyncValue = ref.watch(librarySongsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'VibeFlow',
          style: TextStyle(
            color: Colors.blueAccent,
            fontWeight: FontWeight.w900,
            letterSpacing: -1,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {},
          )
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(syncLibraryProvider);
          await ref.read(syncLibraryProvider.future);
        },
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Library',
                      style: TextStyle(
                        fontSize: 40,
                        fontWeight: FontWeight.bold,
                        letterSpacing: -1.5,
                      ),
                    ),
                    const SizedBox(height: 24),
                    _buildTabs(),
                    const SizedBox(height: 24),
                    _buildGenreChips(),
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
            songsAsyncValue.when(
              data: (songs) {
                if (songs.isEmpty) {
                  return const SliverFillRemaining(
                    child: Center(child: Text('No songs found. Pull to refresh.')),
                  );
                }
                return SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final song = songs[index];
                      return _buildSongItem(song);
                    },
                    childCount: songs.length,
                  ),
                );
              },
              loading: () => const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (err, stack) => SliverFillRemaining(
                child: Center(child: Text('Error: $err')),
              ),
            ),
            const SliverToBoxAdapter(
              child: SizedBox(height: 120), // Bottom padding for mini player & nav
            )
          ],
        ),
      ),
    );
  }

  Widget _buildTabs() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _TabItem(title: 'All Songs', isActive: true),
          const SizedBox(width: 32),
          _TabItem(title: 'Albums', isActive: false),
          const SizedBox(width: 32),
          _TabItem(title: 'Artists', isActive: false),
          const SizedBox(width: 32),
          _TabItem(title: 'Playlists', isActive: false),
        ],
      ),
    );
  }

  Widget _buildGenreChips() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _GenreChip(label: 'All', isActive: true),
          const SizedBox(width: 12),
          _GenreChip(label: 'Punjabi', isActive: false),
          const SizedBox(width: 12),
          _GenreChip(label: 'Hindi', isActive: false),
          const SizedBox(width: 12),
          _GenreChip(label: 'English', isActive: false),
          const SizedBox(width: 12),
          _GenreChip(label: 'Instrumental', isActive: false),
        ],
      ),
    );
  }

  Widget _buildSongItem(song) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 6.0),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.02),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.music_note, color: Colors.white54),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    song.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    song.artist,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 12),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Text(
              _formatDuration(song.durationMs),
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 12,
                fontFamily: 'monospace',
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.more_vert),
              color: Colors.white.withOpacity(0.5),
              onPressed: () {},
            ),
          ],
        ),
      ),
    );
  }

  String _formatDuration(int ms) {
    final duration = Duration(milliseconds: ms);
    final minutes = duration.inMinutes;
    final seconds = duration.inSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }
}

class _TabItem extends StatelessWidget {
  final String title;
  final bool isActive;

  const _TabItem({required this.title, required this.isActive});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: isActive ? Colors.blueAccent : Colors.transparent,
            width: 2.0,
          ),
        ),
      ),
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Text(
        title,
        style: TextStyle(
          color: isActive ? Colors.blueAccent : Colors.white.withOpacity(0.5),
          fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
          fontSize: 18,
        ),
      ),
    );
  }
}

class _GenreChip extends StatelessWidget {
  final String label;
  final bool isActive;

  const _GenreChip({required this.label, required this.isActive});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
      decoration: BoxDecoration(
        color: isActive ? Colors.blueAccent.withOpacity(0.2) : Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isActive ? Colors.cyanAccent : Colors.white.withOpacity(0.5),
          fontWeight: FontWeight.bold,
          fontSize: 14,
        ),
      ),
    );
  }
}
