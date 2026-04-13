import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../player/mini_player.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hour = DateTime.now().hour;
    String greeting = 'Good Evening';
    if (hour < 12) {
      greeting = 'Good Morning';
    } else if (hour < 17) {
      greeting = 'Good Afternoon';
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F131C),
      body: SafeArea(
        child: Stack(
          children: [
            SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        greeting,
                        style: const TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const CircleAvatar(
                        radius: 20,
                        backgroundColor: Colors.blueAccent,
                        child: Icon(Icons.person, color: Colors.white),
                      ),
                    ],
                  ),
                  const SizedBox(height: 32),
                  
                  // Recently Played 2-column grid
                  const Text(
                    'Recently Played',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 16),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      mainAxisSpacing: 16,
                      crossAxisSpacing: 16,
                      childAspectRatio: 2.5,
                    ),
                    itemCount: 4,
                    itemBuilder: (context, index) {
                      return Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 60,
                              height: 60,
                              decoration: BoxDecoration(
                                color: Colors.white12,
                                borderRadius: const BorderRadius.only(
                                  topLeft: Radius.circular(12),
                                  bottomLeft: Radius.circular(12),
                                ),
                              ),
                              child: const Icon(Icons.music_note, color: Colors.white54),
                            ),
                            const SizedBox(width: 8),
                            const Expanded(
                              child: Text(
                                'Recent Album',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                            )
                          ],
                        ),
                      );
                    },
                  ),
                  
                  const SizedBox(height: 32),
                  
                  // Daily Picks (Phase 5 Placeholder)
                  const Text(
                    "Today's Picks",
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    height: 160,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(colors: [Colors.blueAccent.withOpacity(0.2), Colors.cyanAccent.withOpacity(0.1)]),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.blueAccent.withOpacity(0.2)),
                    ),
                    child: const Center(
                      child: Text('AI Recommendations\n(Coming in Phase 5)', textAlign: TextAlign.center, style: TextStyle(color: Colors.blueAccent, fontWeight: FontWeight.bold)),
                    ),
                  ),
                  
                  const SizedBox(height: 32),
                  
                  // Weekend Playlist (Phase 5 Placeholder)
                  const Text(
                    "Weekend Playlist",
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    height: 160,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.purpleAccent.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.purpleAccent.withOpacity(0.2)),
                    ),
                    child: const Center(
                      child: Text('Auto-generated Weekend Mix\n(Coming in Phase 5)', textAlign: TextAlign.center, style: TextStyle(color: Colors.purpleAccent, fontWeight: FontWeight.bold)),
                    ),
                  ),
                  
                  const SizedBox(height: 120), // Bottom padding for mini player
                ],
              ),
            ),
            
            // Floating MiniPlayer
            const Align(
              alignment: Alignment.bottomCenter,
              child: MiniPlayer(),
            ),
          ],
        ),
      ),
    );
  }
}
