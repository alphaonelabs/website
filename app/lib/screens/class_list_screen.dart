import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import 'video_meeting_screen.dart';

class ClassListScreen extends StatefulWidget {
  const ClassListScreen({super.key});

  @override
  State<ClassListScreen> createState() => _ClassListScreenState();
}

class _ClassListScreenState extends State<ClassListScreen> {
  List<Map<String, dynamic>> _classes = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchClasses();
  }

  Future<void> _fetchClasses() async {
    try {
      final token = Provider.of<AuthService>(context, listen: false).token;
      final response = await http.get(
        Uri.parse('https://alphaonelabs.com/api/classes'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _classes = List<Map<String, dynamic>>.from(data['classes']);
          _isLoading = false;
        });
      } else {
        throw Exception('Failed to load classes');
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  void _joinMeeting(Map<String, dynamic> classData) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => VideoMeetingScreen(classData: classData),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Classes'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () {
              Provider.of<AuthService>(context, listen: false).logout();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _classes.isEmpty
              ? const Center(child: Text('No classes found'))
              : ListView.builder(
                  itemCount: _classes.length,
                  itemBuilder: (context, index) {
                    final classData = _classes[index];
                    return Card(
                      margin: const EdgeInsets.all(8.0),
                      child: ListTile(
                        title: Text(classData['name'] ?? 'Unnamed Class'),
                        subtitle: Text(classData['description'] ?? ''),
                        trailing: ElevatedButton(
                          onPressed: () => _joinMeeting(classData),
                          child: const Text('Join Meeting'),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
