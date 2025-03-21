import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:video_app/main.dart';
import 'package:video_app/services/auth_service.dart';
import 'package:video_app/screens/login_screen.dart';
import 'package:video_app/screens/class_list_screen.dart';

void main() {
  group('Video App Tests', () {
    testWidgets('App starts with login screen when not authenticated',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => AuthService()),
          ],
          child: const MyApp(),
        ),
      );

      expect(find.byType(LoginScreen), findsOneWidget);
      expect(find.byType(ClassListScreen), findsNothing);
    });

    testWidgets('Login screen has email and password fields',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ChangeNotifierProvider(
            create: (_) => AuthService(),
            child: const LoginScreen(),
          ),
        ),
      );

      expect(find.byType(TextFormField), findsNWidgets(2));
      expect(find.byType(ElevatedButton), findsOneWidget);
    });

    testWidgets('Login validation shows error messages',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ChangeNotifierProvider(
            create: (_) => AuthService(),
            child: const LoginScreen(),
          ),
        ),
      );

      await tester.tap(find.byType(ElevatedButton));
      await tester.pump();

      expect(find.text('Please enter your email'), findsOneWidget);
      expect(find.text('Please enter your password'), findsOneWidget);
    });

    testWidgets('Email validation checks for @ symbol',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ChangeNotifierProvider(
            create: (_) => AuthService(),
            child: const LoginScreen(),
          ),
        ),
      );

      await tester.enterText(find.byType(TextFormField).first, 'invalidemail');
      await tester.tap(find.byType(ElevatedButton));
      await tester.pump();

      expect(find.text('Please enter a valid email'), findsOneWidget);
    });

    testWidgets('Password validation checks for minimum length',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ChangeNotifierProvider(
            create: (_) => AuthService(),
            child: const LoginScreen(),
          ),
        ),
      );

      await tester.enterText(find.byType(TextFormField).last, '12345');
      await tester.tap(find.byType(ElevatedButton));
      await tester.pump();

      expect(
          find.text('Password must be at least 6 characters'), findsOneWidget);
    });
  });
}
