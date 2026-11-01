import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class AuthService with ChangeNotifier {
  bool _isAuthenticated = false;
  String? _token;
  String? _userId;

  bool get isAuthenticated => _isAuthenticated;
  String? get token => _token;
  String? get userId => _userId;

  Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('http://localhost:8000/api/auth/login/'),
        body: json.encode({
          'email': email,
          'password': password,
        }),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      print('Login response: ${response.body}'); // For debugging

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['status'] == 'success') {
          _token = data['token'];
          _userId = data['userId'].toString();
          _isAuthenticated = true;

          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('token', _token!);
          await prefs.setString('userId', _userId!);

          notifyListeners();
          return true;
        }
      }
      print('Login failed with status code: ${response.statusCode}');
      return false;
    } catch (e) {
      print('Login error: $e');
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
