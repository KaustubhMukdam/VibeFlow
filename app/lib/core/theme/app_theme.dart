import 'package:flutter/material.dart';
import 'color_scheme.dart';

class AppTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: darkColorScheme,
      scaffoldBackgroundColor: darkColorScheme.background,
      appBarTheme: AppBarTheme(
        backgroundColor: darkColorScheme.background,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: darkColorScheme.onBackground),
        titleTextStyle: TextStyle(
          color: darkColorScheme.onBackground,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: darkColorScheme.surface,
        selectedItemColor: darkColorScheme.primary,
        unselectedItemColor: darkColorScheme.onSurface,
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: darkColorScheme.primary,
        inactiveTrackColor: darkColorScheme.primary.withOpacity(0.3),
        thumbColor: darkColorScheme.primary,
        overlayColor: darkColorScheme.primary.withOpacity(0.12),
      ),
      fontFamily: 'Inter', // We can use Inter or Roboto as standard
    );
  }
}
