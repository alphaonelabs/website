# Video Meeting App

A Flutter application that enables teachers to host video meetings and students to connect in a peer-to-peer way. The app integrates with alphaonelabs.com for user authentication and class management.

## Features

- User authentication with alphaonelabs.com
- View enrolled classes
- Join video meetings
- Peer-to-peer video streaming
- Audio mute/unmute
- Video on/off controls
- Responsive UI that works in both portrait and landscape modes

## Requirements

- Flutter SDK (3.0.0 or higher)
- Dart SDK (2.17.0 or higher)
- Android Studio / Xcode for mobile development
- A device with a camera and microphone

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd video-app
```

2. Install dependencies:
```bash
flutter pub get
```

3. Run the app:
```bash
flutter run
```

## Testing

Run the tests using:
```bash
flutter test
```

## Architecture

The app follows a clean architecture pattern with the following structure:

- `lib/`
  - `main.dart` - App entry point
  - `screens/` - UI screens
    - `login_screen.dart`
    - `class_list_screen.dart`
    - `video_meeting_screen.dart`
  - `services/` - Business logic
    - `auth_service.dart`

## WebRTC Implementation

The app uses WebRTC for peer-to-peer video streaming with the following features:

- STUN server configuration for NAT traversal
- SDP negotiation through alphaonelabs.com signaling server
- ICE candidate exchange
- Video and audio track management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 