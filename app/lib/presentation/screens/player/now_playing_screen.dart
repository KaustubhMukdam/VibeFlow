import 'package:flutter/material.dart';

class NowPlayingScreen extends StatelessWidget {
  const NowPlayingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F131C),
      body: SafeArea(
        child: Stack(
          children: [
            Column(
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white.withOpacity(0.1)),
                        ),
                        child: IconButton(
                          icon: const Icon(Icons.keyboard_arrow_down, color: Colors.blueAccent),
                          onPressed: () => Navigator.pop(context),
                        ),
                      ),
                      const Text(
                        'VibeFlow',
                        style: TextStyle(
                          color: Colors.blueAccent,
                          fontWeight: FontWeight.w900,
                          fontSize: 24,
                          letterSpacing: -1,
                        ),
                      ),
                      Row(
                        children: [
                          IconButton(icon: const Icon(Icons.share, color: Colors.white54), onPressed: () {}),
                          IconButton(icon: const Icon(Icons.settings, color: Colors.white54), onPressed: () {}),
                        ],
                      )
                    ],
                  ),
                ),
                
                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      children: [
                        const SizedBox(height: 20),
                        Container(
                          width: 260,
                          height: 260,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(40),
                            color: Colors.blueGrey.shade900,
                            boxShadow: [
                              BoxShadow(
                                color: Colors.cyanAccent.withOpacity(0.2), 
                                blurRadius: 40, 
                                spreadRadius: -10, 
                                offset: const Offset(0, 20)
                              )
                            ],
                          ),
                          child: const Center(
                            child: Icon(Icons.music_note, size: 80, color: Colors.white54),
                          ),
                        ),
                        
                        const SizedBox(height: 32),
                        
                        const Text(
                          'Midnight Circuit',
                          style: TextStyle(fontSize: 40, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: -1),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Lumina Synthesis',
                          style: TextStyle(fontSize: 18, color: Colors.white54, fontWeight: FontWeight.w500),
                        ),
                        
                        const SizedBox(height: 32),
                        SizedBox(
                          height: 60,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: List.generate(30, (index) {
                              return Container(
                                margin: const EdgeInsets.symmetric(horizontal: 2),
                                width: 4,
                                height: 10.0 + (index % 6) * 8.0,
                                decoration: BoxDecoration(
                                  color: Colors.cyanAccent,
                                  borderRadius: BorderRadius.circular(4),
                                  boxShadow: [BoxShadow(color: Colors.cyanAccent.withOpacity(0.4), blurRadius: 4)],
                                ),
                              );
                            }),
                          ),
                        ),
                        
                        const SizedBox(height: 32),
                        
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 32),
                          child: Column(
                            children: [
                              SliderTheme(
                                data: SliderTheme.of(context).copyWith(
                                  trackHeight: 4,
                                  thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                                  overlayShape: const RoundSliderOverlayShape(overlayRadius: 14),
                                ),
                                child: Slider(
                                  value: 0.45,
                                  onChanged: (v) {},
                                  activeColor: Colors.cyanAccent,
                                  inactiveColor: Colors.white12,
                                ),
                              ),
                              const Padding(
                                padding: EdgeInsets.symmetric(horizontal: 16),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text('02:14', style: TextStyle(color: Colors.white54, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 2)),
                                    Text('04:52', style: TextStyle(color: Colors.white54, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 2)),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                        
                        const SizedBox(height: 24),
                        
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 32),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              IconButton(icon: const Icon(Icons.shuffle, color: Colors.white54), onPressed: () {}),
                              Row(
                                children: [
                                  IconButton(icon: const Icon(Icons.skip_previous, size: 32, color: Colors.white), onPressed: () {}),
                                  const SizedBox(width: 24),
                                  Container(
                                    width: 80,
                                    height: 80,
                                    decoration: BoxDecoration(
                                      color: Colors.cyanAccent.withOpacity(0.1),
                                      shape: BoxShape.circle,
                                    ),
                                    child: const Icon(Icons.pause, size: 42, color: Colors.cyanAccent),
                                  ),
                                  const SizedBox(width: 24),
                                  IconButton(icon: const Icon(Icons.skip_next, size: 32, color: Colors.white), onPressed: () {}),
                                ],
                              ),
                              IconButton(icon: const Icon(Icons.repeat, color: Colors.white54), onPressed: () {}),
                            ],
                          ),
                        ),
                        
                        const SizedBox(height: 32),
                        
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.favorite_border, color: Colors.white54),
                            SizedBox(width: 48),
                            Icon(Icons.playlist_add, color: Colors.white54),
                            SizedBox(width: 48),
                            Icon(Icons.queue_music, color: Colors.white54),
                          ],
                        ),
                        
                        const SizedBox(height: 120), 
                      ],
                    ),
                  ),
                ),
              ],
            ),
            
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                height: 90,
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.8),
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(40)),
                  border: Border(top: BorderSide(color: Colors.blueAccent.withOpacity(0.2))),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 20),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('UP NEXT', style: TextStyle(color: Colors.blueAccent, fontWeight: FontWeight.bold, fontSize: 10, letterSpacing: 2)),
                    Icon(Icons.keyboard_arrow_up, color: Colors.white54, size: 20),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
