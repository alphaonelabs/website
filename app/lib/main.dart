import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/login_screen.dart';
import 'screens/class_list_screen.dart';
import 'screens/audio_player_screen.dart';
import 'services/auth_service.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService()),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Video Meeting App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: Consumer<AuthService>(
        builder: (context, authService, _) {
          Widget mainScreen = authService.isAuthenticated
              ? const ClassListScreen()
              : const LoginScreen();

          return Scaffold(
            body: mainScreen,
            floatingActionButton: FloatingActionButton(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) => const AudioPlayerScreen(),
                  ),
                );
              },
              tooltip: 'Audio Player',
              child: const Icon(Icons.music_note),
            ),
          );
        },
      ),
    );
  }
}
