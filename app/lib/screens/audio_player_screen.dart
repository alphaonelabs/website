import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import '../widgets/audio_visualizer.dart';
import 'dart:math' as math;

class AudioPlayerScreen extends StatefulWidget {
  final String? initialAudioPath;

  const AudioPlayerScreen({super.key, this.initialAudioPath});

  @override
  State<AudioPlayerScreen> createState() => _AudioPlayerScreenState();
}

class _AudioPlayerScreenState extends State<AudioPlayerScreen> {
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isPlaying = false;
  Duration _duration = Duration.zero;
  Duration _position = Duration.zero;
  bool _isAudioLoaded = false;
  double _volume = 1.0;
  bool _showVolumeSlider = false;
  List<double> _audioSamples = [];

  @override
  void initState() {
    super.initState();
    _initAudioPlayer();
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _initAudioPlayer() async {
    await _audioPlayer.setVolume(_volume);
    if (widget.initialAudioPath != null) {
      await _loadAudio(widget.initialAudioPath!);
    }

    // Listen to audio position changes to generate visualization data
    _audioPlayer.onPositionChanged.listen((position) {
      if (mounted) {
        setState(() {
          _position = position;
          // Generate simple waveform data based on position
          _audioSamples = List.generate(
            50,
            (i) =>
                math.sin(2 * math.pi * i / 50 + position.inMilliseconds / 100) *
                0.5,
          );
        });
      }
    });

    _audioPlayer.onPlayerStateChanged.listen((state) {
      if (mounted) {
        setState(() {
          _isPlaying = state == PlayerState.playing;
        });
      }
    });

    _audioPlayer.onDurationChanged.listen((duration) {
      if (mounted) {
        setState(() {
          _duration = duration;
          _isAudioLoaded = true;
        });
      }
    });
  }

  Future<void> _loadAudio(String path) async {
    try {
      await _audioPlayer.stop();
      await _audioPlayer.setSource(DeviceFileSource(path));
      setState(() {
        _isAudioLoaded = true;
      });
      await _audioPlayer.resume();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading audio: $e')),
        );
      }
    }
  }

  Future<void> _setVolume(double value) async {
    setState(() {
      _volume = value;
    });
    await _audioPlayer.setVolume(value);
  }

  Future<void> _pickAudioFile() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['mp3'],
      );

      if (result != null && result.files.single.path != null) {
        await _loadAudio(result.files.single.path!);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error picking audio file: $e')),
        );
      }
    }
  }

  String _formatDuration(Duration duration) {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    String twoDigitMinutes = twoDigits(duration.inMinutes.remainder(60));
    String twoDigitSeconds = twoDigits(duration.inSeconds.remainder(60));
    return '$twoDigitMinutes:$twoDigitSeconds';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Audio Player'),
        actions: [
          IconButton(
            icon: const Icon(Icons.file_upload),
            onPressed: _pickAudioFile,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (!_isAudioLoaded)
              const Text(
                'Select an MP3 file to play',
                style: TextStyle(fontSize: 16),
              )
            else ...[
              // Audio visualizer
              AudioVisualizer(
                samples: _audioSamples,
                color: Theme.of(context).primaryColor,
              ),
              const SizedBox(height: 20),

              // Audio progress
              Slider(
                value: _duration.inMilliseconds > 0
                    ? _position.inMilliseconds.toDouble()
                    : 0.0,
                max: _duration.inMilliseconds > 0
                    ? _duration.inMilliseconds.toDouble()
                    : 1.0,
                onChanged: (value) {
                  if (_duration.inMilliseconds > 0) {
                    _audioPlayer.seek(Duration(milliseconds: value.toInt()));
                  }
                },
              ),

              // Duration labels
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(_formatDuration(_position)),
                    Text(_formatDuration(_duration)),
                  ],
                ),
              ),

              // Volume slider (appears when volume button is pressed)
              if (_showVolumeSlider)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0),
                  child: Row(
                    children: [
                      const Icon(Icons.volume_down),
                      Expanded(
                        child: Slider(
                          value: _volume,
                          min: 0.0,
                          max: 1.0,
                          onChanged: _setVolume,
                        ),
                      ),
                      const Icon(Icons.volume_up),
                    ],
                  ),
                ),

              // Playback controls
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.replay_10),
                    onPressed: () {
                      _audioPlayer.seek(
                        Duration(seconds: _position.inSeconds - 10),
                      );
                    },
                  ),
                  IconButton(
                    icon: Icon(
                      _isPlaying
                          ? Icons.pause_circle_filled
                          : Icons.play_circle_filled,
                      size: 48,
                    ),
                    onPressed: () {
                      if (_isPlaying) {
                        _audioPlayer.pause();
                      } else {
                        _audioPlayer.resume();
                      }
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.forward_10),
                    onPressed: () {
                      _audioPlayer.seek(
                        Duration(seconds: _position.inSeconds + 10),
                      );
                    },
                  ),
                  IconButton(
                    icon: Icon(_volume == 0
                        ? Icons.volume_off
                        : _volume < 0.5
                            ? Icons.volume_down
                            : Icons.volume_up),
                    onPressed: () {
                      setState(() {
                        _showVolumeSlider = !_showVolumeSlider;
                      });
                    },
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
