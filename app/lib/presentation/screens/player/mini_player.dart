import 'package:flutter/material.dart';
import 'now_playing_screen.dart';

class MiniPlayer extends StatelessWidget {
  const MiniPlayer({super.key});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const NowPlayingScreen()),
        );
      },
      child: Container(
        height: 64,
        margin: const EdgeInsets.only(left: 24, right: 24, bottom: 80),
        decoration: BoxDecoration(
          color: const Color(0xFF1C2028).withOpacity(0.95),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 20,
              offset: const Offset(0, 10),
            )
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Stack(
            children: [
              Row(
                children: [
                  const SizedBox(width: 12),
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: Colors.white12,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.music_note, color: Colors.white54, size: 20),
                  ),
                  const SizedBox(width: 16),
                  const Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Midnight Circuit',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Lumina Synthesis',
                          style: TextStyle(color: Colors.white54, fontSize: 10),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.devices, color: Colors.cyanAccent, size: 20),
                    onPressed: () {},
                  ),
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: Colors.blueAccent.withOpacity(0.1),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.blueAccent.withOpacity(0.2)),
                    ),
                    child: const Icon(Icons.pause, color: Colors.blueAccent, size: 20),
                  ),
                  const SizedBox(width: 12),
                ],
              ),
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: Container(
                  height: 2,
                  color: Colors.white.withOpacity(0.05),
                  alignment: Alignment.centerLeft,
                  child: FractionallySizedBox(
                    widthFactor: 0.65,
                    child: Container(
                      color: Colors.cyanAccent,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
