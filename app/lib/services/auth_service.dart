import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

const apiBase = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'https://learn.alphaonelabs.com',
);

class AuthService with ChangeNotifier {
  bool _isAuthenticated = false;
  String? _token;
  String? _userId;

  bool get isAuthenticated => _isAuthenticated;
  String? get token => _token;
  String? get userId => _userId;

  Future<bool> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$apiBase/api/login'),
        body: json.encode({
          'username': username,
          'password': password,
        }),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true && data['data'] is Map) {
          final loginData = data['data'] as Map<String, dynamic>;
          final user = loginData['user'] as Map<String, dynamic>?;
          final token = loginData['token']?.toString();
          final userId = user?['id']?.toString();
          if (token == null || token.isEmpty || userId == null) {
            return false;
          }

          _token = token;
          _userId = userId;
          _isAuthenticated = true;

          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('token', _token!);
          await prefs.setString('userId', _userId!);

          notifyListeners();
          return true;
        }
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() async {
    _token = null;
    _userId = null;
    _isAuthenticated = false;

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('userId');

    notifyListeners();
  }

  Future<bool> tryAutoLogin() async {
    final prefs = await SharedPreferences.getInstance();
    if (!prefs.containsKey('token')) return false;

    _token = prefs.getString('token');
    _userId = prefs.getString('userId');
    _isAuthenticated = true;
    notifyListeners();
    return true;
  }
}
