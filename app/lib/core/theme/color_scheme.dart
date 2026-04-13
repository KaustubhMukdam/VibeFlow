import 'package:flutter/material.dart';

const Color primaryColor = Color(0xFFFF9800); // Orange as mentioned in task (animated waveform orange)
const Color backgroundColor = Color(0xFF121212);
const Color surfaceColor = Color(0xFF1E1E1E);
const Color onPrimaryColor = Colors.white;
const Color onBackgroundColor = Colors.white;
const Color onSurfaceColor = Colors.white70;

const ColorScheme darkColorScheme = ColorScheme.dark(
  primary: primaryColor,
  onPrimary: onPrimaryColor,
  background: backgroundColor,
  onBackground: onBackgroundColor,
  surface: surfaceColor,
  onSurface: onSurfaceColor,
  secondary: primaryColor, // Use primary as secondary for a unified look
  onSecondary: onPrimaryColor,
);
