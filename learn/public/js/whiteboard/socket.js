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
    if (this.ws) this.ws.close();

    const safeRoom = encodeURIComponent(roomName || 'main-whiteboard');
    const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const params = new URLSearchParams();

    if (token) {
      params.set('token', token);
    } else {
      params.set('participant_id', guestViewerId);
      params.set('display_name', 'Viewer');
    }

    this.ws = new WebSocket(`${scheme}//${location.host}/api/classroom/${safeRoom}?${params}`);
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
      if (!data?.type) return;
      this._handleMessage(data);
    });
  }

  _handleMessage(data) {
    const h = this.handlers;
    const dispatch = {
      user_info: () => {
        this.currentParticipantId = data.participant_id || '';
        h.onUserInfo(this.currentParticipantId);
      },
      whiteboard_state: () => h.onWhiteboardState(Array.isArray(data.events) ? data.events : []),
      whiteboard_event: () => h.onWhiteboardEvent(data.event || {}),
      whiteboard_clear: () => h.onWhiteboardClear(),
      room_state: () => h.onRoomState(Array.isArray(data.participants) ? data.participants : []),
    };
    dispatch[data.type]?.();
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
}
