// web/static/js/mass_class/student_view.js
document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chatMessages');
    const chatMessage = document.getElementById('chatMessage');
    const sendChat = document.getElementById('sendChat');
    const questionText = document.getElementById('questionText');
    const submitQuestion = document.getElementById('submitQuestion');
    const myQuestionsList = document.getElementById('myQuestionsList');
    const activePoll = document.getElementById('activePoll');
    const noPollsMessage = document.getElementById('noPollsMessage');
    const pollQuestion = document.getElementById('pollQuestion');
    const pollOptions = document.getElementById('pollOptions');
    const submitVote = document.getElementById('submitVote');
    const pollResults = document.getElementById('pollResults');
    const raiseHandBtn = document.getElementById('raiseHandBtn');
    const lowerHandBtn = document.getElementById('lowerHandBtn');
    const handStatus = document.getElementById('handStatus');

    let wsConnection = null;
    let sessionId = null;
    let selectedPollOption = null;
    let handRaised = false;
    let handId = null;
    let activePollId = null;

    // Get session ID from URL
    const pathParts = window.location.pathname.split('/');
    sessionId = pathParts[pathParts.length - 1];

    // Connect to WebSocket
    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/mass-class/view/${sessionId}/`;

      wsConnection = new WebSocket(wsUrl);

      wsConnection.onopen = () => {
        console.log('WebSocket connection established');
      };

      wsConnection.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch(data.type) {
          case 'chat_message':
            addChatMessage(data.username, data.message, data.is_teacher);
            break;

          case 'viewer_count':
            document.getElementById('viewerCount').textContent = data.count;
            break;

          case 'question_answered':
            updateQuestionStatus(data.question_id, 'answered');
            break;

          case 'new_poll':
            showNewPoll(data.poll_id, data.question, data.options);
            break;

          case 'poll_results':
            updatePollResults(data.results);
            break;

          case 'poll_ended':
            hidePoll();
            break;

          case 'hand_raised':
            handId = data.hand_id;
            break;

          case 'hand_acknowledged':
            if (data.hand_id === handId) {
              handAcknowledged();
            }
            break;

          case 'stream_ended':
            showStreamEndedModal();
            break;

          case 'error':
            showError(data.message);
            break;
        }
      };

      wsConnection.onclose = () => {
        console.log('WebSocket connection closed');
        // Try to reconnect after delay
        setTimeout(connectWebSocket, 3000);
      };

      wsConnection.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    }

    // Initialize WebSocket connection
    connectWebSocket();

    // Send message to WebSocket server
    function sendToServer(message) {
      if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
        wsConnection.send(JSON.stringify(message));
      }
    }

    // Chat functionality
    function addChatMessage(username, message, isTeacher) {
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
      const message = chatMessage.value.trim();

      if (message) {
        sendToServer({
          type: 'chat_message',
          message: message
        });

        chatMessage.value = '';
      }
    }

    // Questions functionality
    function submitQuestionToTeacher() {
      const question = questionText.value.trim();

      if (question) {
        sendToServer({
          type: 'ask_question',
          question: question
        });

        // Clear input and show pending
        questionText.value = '';
        addMyQuestion('pending', question);
      }
    }

    function addMyQuestion(status, questionText) {
      const questionElement = document.createElement('div');
      questionElement.className = `my-question ${status}`;
      questionElement.innerHTML = `
        <div class="question-text">${questionText}</div>
        <div class="question-status">Status: ${status === 'pending' ? 'Waiting for answer' : 'Answered'}</div>
      `;
      myQuestionsList.appendChild(questionElement);
    }

    function updateQuestionStatus(questionId, status) {
      const questionElement = document.querySelector(`.my-question[data-id="${questionId}"]`);
      if (questionElement) {
        questionElement.classList.remove('pending');
        questionElement.classList.add(status);
        questionElement.querySelector('.question-status').textContent = 'Status: Answered';
      }
    }

    // Poll functionality
    function showNewPoll(pollId, question, options) {
      activePollId = pollId;
      selectedPollOption = null;

      // Display the poll
      noPollsMessage.classList.add('hidden');
      activePoll.classList.remove('hidden');
      pollResults.classList.add('hidden');

      // Set question
      pollQuestion.textContent = question;

      // Clear existing options
      pollOptions.innerHTML = '';

      // Add options
      options.forEach((option, index) => {
        const optionElement = document.createElement('div');
        optionElement.className = 'poll-option';
        optionElement.innerHTML = `
          <label>
            <input type="radio" name="pollOption" value="${index}">
            <span>${option}</span>
          </label>
        `;
        pollOptions.appendChild(optionElement);

        // Add click event
        const radioButton = optionElement.querySelector('input[type="radio"]');
        radioButton.addEventListener('change', () => {
          selectedPollOption = index;
        });
      });

      // Show the submit button
      submitVote.classList.remove('hidden');
    }

    function submitPollVote() {
      if (selectedPollOption !== null && activePollId) {
        sendToServer({
          type: 'poll_vote',
          poll_id: activePollId,
          option_index: selectedPollOption
        });

        // Hide the options and submit button
        pollOptions.classList.add('hidden');
        submitVote.classList.add('hidden');

        // Show the results
        pollResults.classList.remove('hidden');
      } else {
        showError('Please select an option');
      }
    }

    function updatePollResults(results) {
      // Clear previous results
      pollResults.innerHTML = '';

      // Calculate total votes
      const totalVotes = results.reduce((sum, option) => sum + option.count, 0);

      // Add new results
      results.forEach(result => {
        const percentage = totalVotes > 0 ? Math.round((result.count / totalVotes) * 100) : 0;

        const resultElement = document.createElement('div');
        resultElement.className = 'poll-result';
        resultElement.innerHTML = `
          <div class="poll-option-text">${result.text}</div>
          <div class="poll-option-bar-container">
            <div class="poll-option-bar" style="width: ${percentage}%"></div>
            <span class="poll-option-percentage">${percentage}%</span>
          </div>
          <div class="poll-option-count">${result.count} vote${result.count !== 1 ? 's' : ''}</div>
        `;

        pollResults.appendChild(resultElement);
      });
    }

    function hidePoll() {
      activePoll.classList.add('hidden');
      noPollsMessage.classList.remove('hidden');
      activePollId = null;
    }

    // Hand raising functionality
    function raiseHand() {
      if (!handRaised) {
        sendToServer({
          type: 'raise_hand'
        });

        handRaised = true;
        raiseHandBtn.disabled = true;
        handStatus.classList.remove('hidden');
      }
    }

    function lowerHand() {
      if (handRaised) {
        sendToServer({
          type: 'lower_hand',
          hand_id: handId
        });

        handRaised = false;
        handId = null;
        raiseHandBtn.disabled = false;
        handStatus.classList.add('hidden');
      }
    }

    function handAcknowledged() {
      const statusMessage = handStatus.querySelector('p');
      statusMessage.textContent = 'The teacher has acknowledged your raised hand!';
      statusMessage.classList.add('acknowledged');
    }

    // Error handling
    function showError(message) {
      // Simple error notification
      alert(message);
    }

    // Stream ended
    function showStreamEndedModal() {
      document.getElementById('streamEndedModal').classList.remove('hidden');
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
    sendChat.addEventListener('click', sendChatMessage);
    chatMessage.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendChatMessage();
    });

    submitQuestion.addEventListener('click', submitQuestionToTeacher);

    submitVote.addEventListener('click', submitPollVote);

    raiseHandBtn.addEventListener('click', raiseHand);
    lowerHandBtn.addEventListener('click', lowerHand);
  });
