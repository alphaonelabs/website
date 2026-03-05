// web/static/js/mass_class/teacher_broadcast.js
document.addEventListener('DOMContentLoaded', function() {
    const localVideo = document.getElementById('localVideo');
    const webcamVideo = document.getElementById('webcamVideo');
    const startStreamBtn = document.getElementById('startStream');
    const stopStreamBtn = document.getElementById('stopStream');
    const streamStatus = document.getElementById('streamStatus');

    let displayStream = null;
    let webcamStream = null;
    let peerConnection = null;
    let mediaRecorder = null;
    let wsConnection = null;
    let streamActive = false;
    let streamStartTime = null;
    let sessionId = null;

    // WebRTC configuration
    const configuration = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
      ]
    };

    // Connect to signaling server
    function connectSignaling() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/mass-class/broadcast/`;

      wsConnection = new WebSocket(wsUrl);

      wsConnection.onopen = () => {
        console.log('WebSocket connection established');
      };

      wsConnection.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch(data.type) {
          case 'session_created':
            sessionId = data.session_id;
            setupWebRTC();
            break;

          case 'ice_candidate':
            if (peerConnection && data.candidate) {
              peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate))
                .catch(e => console.error('Error adding ICE candidate:', e));
            }
            break;

          case 'answer':
            if (peerConnection) {
              peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp))
                .catch(e => console.error('Error setting remote description:', e));
            }
            break;

          case 'stream_started':
            streamActive = true;
            streamStartTime = new Date();
            updateUI(true);
            closeModal();
            break;

          case 'stream_error':
            alert(`Streaming error: ${data.message}`);
            stopStreaming();
            closeModal();
            break;

          case 'viewer_count':
            document.getElementById('viewerCount').textContent = data.count;
            break;

          case 'chat_message':
            addChatMessage(data.username, data.message, false);
            break;

          case 'question':
            addQuestion(data.id, data.username, data.question);
            break;

          case 'poll_results':
            updatePollResults(data.results);
            break;
        }
      };

      wsConnection.onclose = () => {
        console.log('WebSocket connection closed');
        if (streamActive) {
          stopStreaming();
        }
      };

      wsConnection.onerror = (error) => {
        console.error('WebSocket error:', error);
        alert('Connection error. Please try again later.');
      };
    }

    // Set up WebRTC connection
    async function setupWebRTC() {
      try {
        // Get screen display
        displayStream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            width: { ideal: 1920 },
            height: { ideal: 1080 },
            frameRate: { ideal: 30 }
          }
        });

        // Get webcam
        webcamStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true
        });

        // Display streams in preview
        localVideo.srcObject = displayStream;
        webcamVideo.srcObject = webcamStream;

        // Create peer connection
        peerConnection = new RTCPeerConnection(configuration);

        // Add tracks to peer connection
        displayStream.getVideoTracks().forEach(track => {
          peerConnection.addTrack(track, displayStream);
        });

        webcamStream.getAudioTracks().forEach(track => {
          peerConnection.addTrack(track, webcamStream);
        });

        // Handle ICE candidates
        peerConnection.onicecandidate = (event) => {
          if (event.candidate) {
            sendToServer({
              type: 'ice_candidate',
              candidate: event.candidate,
              session_id: sessionId
            });
          }
        };

        // Create and send offer
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);

        sendToServer({
          type: 'offer',
          sdp: peerConnection.localDescription,
          session_id: sessionId
        });

      } catch (error) {
        console.error('Error setting up WebRTC:', error);
        alert(`Failed to access media devices: ${error.message}`);
        closeModal();
      }
    }

    // Send message to signaling server
    function sendToServer(message) {
      if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
        wsConnection.send(JSON.stringify(message));
      }
    }

    // Start streaming
    function startStreaming() {
      if (streamActive) return;

      openModal();
      connectSignaling();
    }

    // Stop streaming
    function stopStreaming() {
      if (!streamActive) return;

      sendToServer({
        type: 'stop_stream',
        session_id: sessionId
      });

      if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
      }

      if (displayStream) {
        displayStream.getTracks().forEach(track => track.stop());
        displayStream = null;
      }

      if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
      }

      localVideo.srcObject = null;
      webcamVideo.srcObject = null;

      streamActive = false;
      sessionId = null;
      streamStartTime = null;

      updateUI(false);
    }

    // Modal handling
    function openModal() {
      document.getElementById('streamingModal').style.display = 'flex';
    }

    function closeModal() {
      document.getElementById('streamingModal').style.display = 'none';
    }

    // UI updates
    function updateUI(isStreaming) {
      startStreamBtn.disabled = isStreaming;
      stopStreamBtn.disabled = !isStreaming;
      streamStatus.textContent = isStreaming ? 'Live' : 'Offline';
      streamStatus.className = isStreaming ? 'status-live' : 'status-offline';

      if (isStreaming) {
        // Start duration timer
        setInterval(updateStreamDuration, 1000);

        // Get video resolution
        if (displayStream && displayStream.getVideoTracks().length > 0) {
          const videoTrack = displayStream.getVideoTracks()[0];
          const settings = videoTrack.getSettings();
          document.getElementById('streamResolution').textContent =
            `${settings.width}x${settings.height}`;
        }
      }
    }

    // Update stream duration
    function updateStreamDuration() {
      if (!streamActive || !streamStartTime) return;

      const now = new Date();
      const diff = now - streamStartTime;

      const hours = Math.floor(diff / 3600000).toString().padStart(2, '0');
      const minutes = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0');
      const seconds = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0');

      document.getElementById('streamDuration').textContent =
        `${hours}:${minutes}:${seconds}`;
    }

    // Chat functionality
    function addChatMessage(username, message, isTeacher) {
      const chatMessages = document.getElementById('chatMessages');
      const messageElement = document.createElement('div');
      messageElement.className = `chat-message ${isTeacher ? 'teacher-message' : ''}`;
      messageElement.innerHTML = `
        <span class="message-sender">${username}${isTeacher ? ' (Teacher)' : ''}:</span>
        <span class="message-text">${message}</span>
      `;
      chatMessages.appendChild(messageElement);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function sendChatMessage() {
      const messageInput = document.getElementById('chatMessage');
      const message = messageInput.value.trim();

      if (message && streamActive) {
        sendToServer({
          type: 'chat_message',
          message: message,
          session_id: sessionId
        });

        addChatMessage('You', message, true);
        messageInput.value = '';
      }
    }

    // Poll functionality
    function createPoll() {
      const question = document.getElementById('pollQuestion').value.trim();
      if (!question) return;

      const optionInputs = document.querySelectorAll('.poll-option-input');
      const options = [];

      optionInputs.forEach(input => {
        const option = input.value.trim();
        if (option) {
          options.push(option);
        }
      });

      if (options.length < 2) {
        alert('Please add at least 2 poll options');
        return;
      }

      sendToServer({
        type: 'create_poll',
        question: question,
        options: options,
        session_id: sessionId
      });

      document.getElementById('activePollQuestion').textContent = question;
      document.getElementById('activePoll').classList.remove('hidden');
      document.getElementById('pollResults').innerHTML = '';

      options.forEach(option => {
        const resultElement = document.createElement('div');
        resultElement.className = 'poll-result';
        resultElement.innerHTML = `
          <div class="poll-option-text">${option}</div>
          <div class="poll-option-bar-container">
            <div class="poll-option-bar" style="width: 0%"></div>
            <span class="poll-option-percentage">0%</span>
          </div>
          <div class="poll-option-count">0 votes</div>
        `;
        document.getElementById('pollResults').appendChild(resultElement);
      });
    }

    function updatePollResults(results) {
      const totalVotes = results.reduce((sum, option) => sum + option.count, 0);
      const resultElements = document.querySelectorAll('.poll-result');

      results.forEach((result, index) => {
        if (index < resultElements.length) {
          const percentage = totalVotes > 0 ? Math.round((result.count / totalVotes) * 100) : 0;
          const element = resultElements[index];

          element.querySelector('.poll-option-bar').style.width = `${percentage}%`;
          element.querySelector('.poll-option-percentage').textContent = `${percentage}%`;
          element.querySelector('.poll-option-count').textContent =
            `${result.count} vote${result.count !== 1 ? 's' : ''}`;
        }
      });
    }

    function endPoll() {
      sendToServer({
        type: 'end_poll',
        session_id: sessionId
      });

      document.getElementById('activePoll').classList.add('hidden');
      document.getElementById('pollQuestion').value = '';

      const optionInputs = document.querySelectorAll('.poll-option-input');
      optionInputs.forEach(input => {
        input.value = '';
      });

      // Remove extra poll options (keep first two)
      const pollOptions = document.getElementById('pollOptions');
      while (pollOptions.children.length > 2) {
        pollOptions.removeChild(pollOptions.lastChild);
      }
    }

    // Questions functionality
    function addQuestion(id, username, question) {
      const questionsList = document.getElementById('questionsList');
      const questionElement = document.createElement('div');
      questionElement.className = 'question-item';
      questionElement.dataset.id = id;
      questionElement.innerHTML = `
        <div class="question-header">
          <span class="question-username">${username}</span>
          <span class="question-time">${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="question-text">${question}</div>
      `;
      questionsList.appendChild(questionElement);

      // Add selection event
      questionElement.addEventListener('click', () => {
        const selected = document.querySelector('.question-item.selected');
        if (selected) {
          selected.classList.remove('selected');
        }
        questionElement.classList.add('selected');
        document.getElementById('answerQuestion').disabled = false;
        document.getElementById('dismissQuestion').disabled = false;
      });
    }

    function answerQuestion() {
      const selected = document.querySelector('.question-item.selected');
      if (!selected) return;

      const questionId = selected.dataset.id;

      sendToServer({
        type: 'answer_question',
        question_id: questionId,
        session_id: sessionId
      });

      selected.classList.add('answered');
      selected.classList.remove('selected');
      document.getElementById('answerQuestion').disabled = true;
      document.getElementById('dismissQuestion').disabled = true;
    }

    function dismissQuestion() {
      const selected = document.querySelector('.question-item.selected');
      if (!selected) return;

      const questionId = selected.dataset.id;

      sendToServer({
        type: 'dismiss_question',
        question_id: questionId,
        session_id: sessionId
      });

      selected.remove();
      document.getElementById('answerQuestion').disabled = true;
      document.getElementById('dismissQuestion').disabled = true;
    }

    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const tabName = button.dataset.tab;

        // Update active tab button
        tabButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        // Show active tab content
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => content.classList.add('hidden'));
        document.getElementById(`${tabName}Tab`).classList.remove('hidden');
      });
    });

    // Event listeners
    startStreamBtn.addEventListener('click', startStreaming);
    stopStreamBtn.addEventListener('click', stopStreaming);

    document.getElementById('sendChat').addEventListener('click', sendChatMessage);
    document.getElementById('chatMessage').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendChatMessage();
    });

    document.getElementById('addPollOption').addEventListener('click', () => {
      const pollOptions = document.getElementById('pollOptions');
      const newOption = document.createElement('div');
      newOption.className = 'poll-option';
      newOption.innerHTML = `
        <input type="text" placeholder="Option ${pollOptions.children.length + 1}" class="poll-option-input">
      `;
      pollOptions.appendChild(newOption);
    });

    document.getElementById('launchPoll').addEventListener('click', createPoll);
    document.getElementById('endPoll').addEventListener('click', endPoll);

    document.getElementById('answerQuestion').addEventListener('click', answerQuestion);
    document.getElementById('dismissQuestion').addEventListener('click', dismissQuestion);
  });
