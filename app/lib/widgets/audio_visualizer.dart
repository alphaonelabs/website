import 'package:flutter/material.dart';

class AudioVisualizer extends StatelessWidget {
  final List<double> samples;
  final Color color;

  const AudioVisualizer({
    super.key,
    required this.samples,
    this.color = Colors.blue,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 100,
      width: double.infinity,
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: CustomPaint(
          painter: WaveformPainter(
            samples: samples,
            color: color,
          ),
          size: const Size(double.infinity, 100),
        ),
      ),
    );
  }
}

class WaveformPainter extends CustomPainter {
  final List<double> samples;
  final Color color;
  final Paint waveformPaint;
  final Paint centerLinePaint;

  WaveformPainter({
    required this.samples,
    required this.color,
  })  : waveformPaint = Paint()
          ..color = color
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke,
        centerLinePaint = Paint()
          ..color = Colors.grey.shade300
          ..strokeWidth = 1
          ..style = PaintingStyle.stroke;

  @override
  void paint(Canvas canvas, Size size) {
    // Draw center line
    final centerY = size.height / 2;
    canvas.drawLine(
      Offset(0, centerY),
      Offset(size.width, centerY),
      centerLinePaint,
    );

    if (samples.isEmpty) return;

    final path = Path();
    final pointsPerSample = size.width / samples.length;

    // Start at the left edge
    path.moveTo(0, centerY);

    // Draw the waveform
    for (var i = 0; i < samples.length; i++) {
      final x = i * pointsPerSample;
      final y = centerY + (samples[i] * size.height / 2);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, waveformPaint);
  }

  @override
  bool shouldRepaint(WaveformPainter oldDelegate) =>
      samples != oldDelegate.samples || color != oldDelegate.color;
}
