/**
 * WebSocket manager for realtime collaborative whiteboard sessions.
 */

export class WhiteboardSocket {
  constructor(handlers = {}) {
    this.handlers = {
      onStatusChange: handlers.onStatusChange || (() => {}),
      onUserInfo: handlers.onUserInfo || (() => {}),
      onWhiteboardState: handlers.onWhiteboardState || (() => {}),
      onWhiteboardEvent: handlers.onWhiteboardEvent || (() => {}),
      onWhiteboardClear: handlers.onWhiteboardClear || (() => {}),
      onRoomState: handlers.onRoomState || (() => {}),
    };
    this.ws = null;
    this.currentParticipantId = '';
  }

  isOpen() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  connect(roomName, token, guestViewerId) {
    if (this.ws) {
      this.ws.close();
    }

    const safeRoom = encodeURIComponent(roomName || 'main-whiteboard');
    const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const params = new URLSearchParams();

    if (token) {
      params.set('token', token);
    } else {
      params.set('participant_id', guestViewerId);
      params.set('display_name', 'Viewer');
    }

    const wsUrl = `${scheme}//${location.host}/api/classroom/${safeRoom}?${params.toString()}`;
    this.ws = new WebSocket(wsUrl);

    this.handlers.onStatusChange('Connecting...', false);

    this.ws.addEventListener('open', () => {
      this.handlers.onStatusChange(token ? 'Connected' : 'Viewing live board', true);
    });

    this.ws.addEventListener('close', () => {
      this.handlers.onStatusChange('Disconnected', false);
    });

    this.ws.addEventListener('message', (message) => {
      let data = null;
      try {
        data = JSON.parse(message.data);
      } catch (_) {
        return;
      }
      if (!data || !data.type) return;

      if (data.type === 'user_info') {
        this.currentParticipantId = data.participant_id || '';
        this.handlers.onUserInfo(this.currentParticipantId);
      } else if (data.type === 'whiteboard_state') {
        this.handlers.onWhiteboardState(Array.isArray(data.events) ? data.events : []);
      } else if (data.type === 'whiteboard_event') {
        this.handlers.onWhiteboardEvent(data.event || {});
      } else if (data.type === 'whiteboard_clear') {
        this.handlers.onWhiteboardClear();
      } else if (data.type === 'room_state') {
        this.handlers.onRoomState(Array.isArray(data.participants) ? data.participants : []);
      }
    });
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendEvent(event) {
    if (this.isOpen()) {
      this.ws.send(JSON.stringify({ type: 'whiteboard_event', event }));
    }
  }

  clearRoom() {
    if (this.isOpen()) {
      this.ws.send(JSON.stringify({ type: 'whiteboard_clear' }));
    }
  }

  undo() {
    if (this.isOpen()) {
      this.ws.send(JSON.stringify({ type: 'whiteboard_undo' }));
    }
  }
}
