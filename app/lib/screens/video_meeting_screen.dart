import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';

class VideoMeetingScreen extends StatefulWidget {
  final Map<String, dynamic> classData;

  const VideoMeetingScreen({super.key, required this.classData});

  @override
  State<VideoMeetingScreen> createState() => _VideoMeetingScreenState();
}

class _VideoMeetingScreenState extends State<VideoMeetingScreen> {
  RTCPeerConnection? _peerConnection;
  MediaStream? _localStream;
  MediaStream? _remoteStream;
  final _localRenderer = RTCVideoRenderer();
  final _remoteRenderer = RTCVideoRenderer();
  bool _isMuted = false;
  bool _isVideoOff = false;

  @override
  void initState() {
    super.initState();
    _initRenderers();
    _joinMeeting();
  }

  Future<void> _initRenderers() async {
    await _localRenderer.initialize();
    await _remoteRenderer.initialize();
  }

  Future<void> _joinMeeting() async {
    try {
      // Get user media
      final mediaConstraints = <String, dynamic>{
        'audio': true,
        'video': {
          'mandatory': {
            'minWidth': '640',
            'minHeight': '480',
            'minFrameRate': '30',
          },
          'facingMode': 'user',
          'optional': [],
        }
      };

      _localStream =
          await navigator.mediaDevices.getUserMedia(mediaConstraints);
      _localRenderer.srcObject = _localStream;

      // Create peer connection
      final configuration = <String, dynamic>{
        'iceServers': [
          {'urls': 'stun:stun.l.google.com:19302'},
        ],
      };

      _peerConnection = await createPeerConnection(configuration, {});

      // Add local stream to peer connection
      _localStream!.getTracks().forEach((track) {
        _peerConnection!.addTrack(track, _localStream!);
      });

      // Set up event handlers
      _peerConnection!.onIceCandidate = (candidate) {
        // Send candidate to signaling server
        _sendIceCandidate(candidate);
      };

      _peerConnection!.onTrack = (event) {
        if (event.streams.isNotEmpty) {
          _remoteRenderer.srcObject = event.streams[0];
          setState(() => _remoteStream = event.streams[0]);
        }
      };

      // Connect to signaling server and exchange SDP
      await _connectToSignalingServer();
    } catch (e) {
      print('Error joining meeting: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error joining meeting: $e')),
        );
      }
    }
  }

  Future<void> _connectToSignalingServer() async {
    try {
      final token = Provider.of<AuthService>(context, listen: false).token;
      final response = await http.post(
        Uri.parse('https://alphaonelabs.com/api/meetings/join'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'classId': widget.classData['id'],
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Handle signaling data (e.g., SDP offer/answer)
        if (data['type'] == 'offer') {
          await _handleOffer(data['sdp']);
        }
      }
    } catch (e) {
      print('Signaling server error: $e');
    }
  }

  Future<void> _handleOffer(String sdp) async {
    try {
      await _peerConnection!.setRemoteDescription(
        RTCSessionDescription(sdp, 'offer'),
      );

      final answer = await _peerConnection!.createAnswer();
      await _peerConnection!.setLocalDescription(answer);

      // Send answer to signaling server
      final token = Provider.of<AuthService>(context, listen: false).token;
      await http.post(
        Uri.parse('https://alphaonelabs.com/api/meetings/answer'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'classId': widget.classData['id'],
          'sdp': answer.sdp,
          'type': answer.type,
        }),
      );
    } catch (e) {
      print('Error handling offer: $e');
    }
  }

  Future<void> _sendIceCandidate(RTCIceCandidate candidate) async {
    try {
      final token = Provider.of<AuthService>(context, listen: false).token;
      await http.post(
        Uri.parse('https://alphaonelabs.com/api/meetings/ice-candidate'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'classId': widget.classData['id'],
          'candidate': candidate.toMap(),
        }),
      );
    } catch (e) {
      print('Error sending ICE candidate: $e');
    }
  }

  void _toggleMute() {
    if (_localStream != null) {
      final audioTrack = _localStream!.getAudioTracks().first;
      setState(() {
        _isMuted = !_isMuted;
        audioTrack.enabled = !_isMuted;
      });
    }
  }

  void _toggleVideo() {
    if (_localStream != null) {
      final videoTrack = _localStream!.getVideoTracks().first;
      setState(() {
        _isVideoOff = !_isVideoOff;
        videoTrack.enabled = !_isVideoOff;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.classData['name'] ?? 'Video Meeting'),
        actions: [
          IconButton(
            icon: Icon(_isMuted ? Icons.mic_off : Icons.mic),
            onPressed: _toggleMute,
          ),
          IconButton(
            icon: Icon(_isVideoOff ? Icons.videocam_off : Icons.videocam),
            onPressed: _toggleVideo,
          ),
        ],
      ),
      body: OrientationBuilder(
        builder: (context, orientation) {
          return Stack(
            children: [
              Container(
                margin: const EdgeInsets.all(8.0),
                child: RTCVideoView(
                  _remoteRenderer,
                  objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover,
                ),
              ),
              Positioned(
                right: 16,
                bottom: 16,
                child: Container(
                  width: 120,
                  height: 160,
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.white, width: 2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: RTCVideoView(
                      _localRenderer,
                      mirror: true,
                      objectFit:
                          RTCVideoViewObjectFit.RTCVideoViewObjectFitCover,
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  void dispose() {
    _localStream?.dispose();
    _remoteStream?.dispose();
    _peerConnection?.dispose();
    _localRenderer.dispose();
    _remoteRenderer.dispose();
    super.dispose();
  }
}
