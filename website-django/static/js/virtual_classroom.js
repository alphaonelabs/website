document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();

    // Cache for container rect to avoid layout recalculations
    let cachedRect = null;

    function refreshContainerRect() {
        cachedRect = classroomContainer.getBoundingClientRect();
    }

    // Add interaction state
    const interactionState = {
        nearInteractive: false,
        currentInteractive: null,
        interactiveElements: {
            blackboard: { x: 0, y: 0, width: 0, height: 0 },
            teacherDesk: { x: 0, y: 0, width: 0, height: 0 },
            seats: []
        },
        occupiedSeats: new Set() // Track which seats are occupied
    };

    // Track other participants' positions and states
    const otherParticipants = new Map(); // Map of username -> participant data

    // Helper function to check if character is near an interactive element
    function isNearInteractive(charX, charY, element, threshold = 50) {
        const centerX = element.x + element.width / 2;
        const centerY = element.y + element.height / 2;
        const distance = Math.sqrt(
            Math.pow(charX - centerX, 2) +
            Math.pow(charY - centerY, 2)
        );
        return distance < threshold;
    }

    // Add interaction popup
    function showInteractionPopup(message) {
        hideInteractionPopup();

        // Different message if user is seated
        if (state.isSeated) {
            if (message.includes('seat')) {
                message = 'Press E to stand up';
            } else {
                message = 'Stand up first to interact with other elements';
            }
        }

        const popup = document.createElement('div');
        popup.id = 'interaction-popup';
        popup.className = 'fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-black bg-opacity-75 text-white px-4 py-2 rounded-lg z-50 pointer-events-none';
        popup.textContent = message;

        document.body.appendChild(popup);

        // Auto-hide after 3 seconds
        setTimeout(() => {
            hideInteractionPopup();
        }, 3000);
    }

    function hideInteractionPopup() {
        const popup = document.getElementById('interaction-popup');
        if (popup) {
            popup.remove();
        }
    }

    // Handle keyboard interactions
    window.addEventListener('keydown', (e) => {
        if (e.key.toLowerCase() === 'e' && interactionState.nearInteractive) {
            const element = interactionState.currentInteractive;
            if (element) {
                if (element.startsWith('seat-')) {
                    if (state.isSeated && state.currentSeat === element) {
                        // Stand up from current seat
                        if (socket && socket.readyState === WebSocket.OPEN) {
                            socket.send(JSON.stringify({
                                type: 'leave_seat',
                                seat_id: element
                            }));
                        }
                        state.isSeated = false;
                        state.currentSeat = null;
                    } else if (!state.isSeated) {
                        // Check if seat is occupied before trying to take it
                        if (isSeatOccupied(element)) {
                            showNotification('This seat is already taken by another student.', 'warning');
                        } else {
                            // Take the seat
                            if (socket && socket.readyState === WebSocket.OPEN) {
                                socket.send(JSON.stringify({
                                    type: 'update_seat',
                                    seat_id: element
                                }));
                            }
                            // Optimistically update state (will be corrected if seat is actually occupied)
                            state.isSeated = true;
                            state.currentSeat = element;
                        }
                    }
                } else {
                    // Only allow other interactions if not seated
                    if (!state.isSeated) {
                        let redirectUrl = '';
                        switch (element) {
                            case 'blackboard':
                                redirectUrl = `/whiteboard/${classroomId}/`;
                                break;
                            case 'teacherDesk':
                                redirectUrl = `/virtual-classroom/${classroomId}/attendance/`;
                                break;
                        }
                        if (redirectUrl) {
                            window.location.href = redirectUrl;
                        }
                    }
                }
            }
        }
    });

    // Helper function to darken colors
    function darkenColor(hex, percent) {
        let r = parseInt(hex.substring(1, 3), 16);
        let g = parseInt(hex.substring(3, 5), 16);
        let b = parseInt(hex.substring(5, 7), 16);

        r = Math.floor(r * (100 - percent) / 100);
        g = Math.floor(g * (100 - percent) / 100);
        b = Math.floor(b * (100 - percent) / 100);

        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    // Load settings from form data (which comes from the database)
    function loadSettings() {
        // Read values from the form
        const settings = {
            wall_color: document.getElementById('wallColor').value,
            floor_color: document.getElementById('floorColor').value,
            desk_color: document.getElementById('deskColor').value,
            chair_color: document.getElementById('chairColor').value,
            board_color: document.getElementById('boardColor').value,
            number_of_rows: parseInt(document.getElementById('numRows').value),
            desks_per_row: parseInt(document.getElementById('desksPerRow').value),
            has_plants: document.getElementById('hasPlants').checked,
            has_windows: document.getElementById('hasWindows').checked,
            has_bookshelf: document.getElementById('hasBookshelf').checked,
            has_clock: document.getElementById('hasClock').checked,
            has_carpet: document.getElementById('hasCarpet').checked
        };

        return settings;
    }

    // Initialize state with settings from form
    const state = {
        settings: loadSettings(),
        character: {
            position: { x: 400, y: 300 },
            velocity: { x: 0, y: 0 },
            direction: 'down',
            isMoving: false,
            walkFrame: 0
        },
        keysPressed: {},
        lastUpdateTime: Date.now(),
        isSeated: false,
        currentSeat: null
    };

    // Initialize COLORS and SETTINGS from state
    const COLORS = {
        WALL: state.settings.wall_color,
        FLOOR: state.settings.floor_color,
        DESK: state.settings.desk_color,
        CHAIR: state.settings.chair_color,
        BOARD: state.settings.board_color
    };

    const SETTINGS = {
        NUM_ROWS: state.settings.number_of_rows,
        DESKS_PER_ROW: state.settings.desks_per_row,
        HAS_PLANTS: state.settings.has_plants,
        HAS_WINDOWS: state.settings.has_windows,
        HAS_BOOKSHELF: state.settings.has_bookshelf,
        HAS_CLOCK: state.settings.has_clock,
        HAS_CARPET: state.settings.has_carpet
    };

    // Save settings to database via AJAX
    function saveSettings(settings) {
        const data = {
            wall_color: settings.wall_color,
            floor_color: settings.floor_color,
            desk_color: settings.desk_color,
            chair_color: settings.chair_color,
            board_color: settings.board_color,
            number_of_rows: settings.number_of_rows,
            desks_per_row: settings.desks_per_row,
            has_plants: settings.has_plants,
            has_windows: settings.has_windows,
            has_bookshelf: settings.has_bookshelf,
            has_clock: settings.has_clock,
            has_carpet: settings.has_carpet
        };

        fetch(window.location.href, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log('Customization saved successfully');

                    // Update state and constants
                    state.settings = settings;
                    COLORS.WALL = settings.wall_color;
                    COLORS.FLOOR = settings.floor_color;
                    COLORS.DESK = settings.desk_color;
                    COLORS.CHAIR = settings.chair_color;
                    COLORS.BOARD = settings.board_color;

                    SETTINGS.NUM_ROWS = settings.number_of_rows;
                    SETTINGS.DESKS_PER_ROW = settings.desks_per_row;
                    SETTINGS.HAS_PLANTS = settings.has_plants;
                    SETTINGS.HAS_WINDOWS = settings.has_windows;
                    SETTINGS.HAS_BOOKSHELF = settings.has_bookshelf;
                    SETTINGS.HAS_CLOCK = settings.has_clock;
                    SETTINGS.HAS_CARPET = settings.has_carpet;

                    // Re-render the classroom with updated settings
                    renderClassroom();
                }
            })
            .catch(error => console.error('Error saving customization:', error));
    }

    // Update form values to match settings
    function updateFormValues(settings) {
        // Update color inputs
        document.getElementById('wallColor').value = settings.wall_color;
        document.getElementById('wallColorValue').textContent = settings.wall_color;

        document.getElementById('floorColor').value = settings.floor_color;
        document.getElementById('floorColorValue').textContent = settings.floor_color;

        document.getElementById('deskColor').value = settings.desk_color;
        document.getElementById('deskColorValue').textContent = settings.desk_color;

        document.getElementById('chairColor').value = settings.chair_color;
        document.getElementById('chairColorValue').textContent = settings.chair_color;

        document.getElementById('boardColor').value = settings.board_color;
        document.getElementById('boardColorValue').textContent = settings.board_color;

        // Update range inputs
        const numRowsInput = document.getElementById('numRows');
        const numRowsValue = document.getElementById('numRowsValue');
        if (numRowsInput && numRowsValue) {
            numRowsInput.value = settings.number_of_rows;
            numRowsValue.textContent = settings.number_of_rows;
        }

        const desksPerRowInput = document.getElementById('desksPerRow');
        const desksPerRowValue = document.getElementById('desksPerRowValue');
        if (desksPerRowInput && desksPerRowValue) {
            desksPerRowInput.value = settings.desks_per_row;
            desksPerRowValue.textContent = settings.desks_per_row;
        }

        // Update checkboxes
        const checkboxes = {
            'hasPlants': settings.has_plants,
            'hasWindows': settings.has_windows,
            'hasBookshelf': settings.has_bookshelf,
            'hasClock': settings.has_clock,
            'hasCarpet': settings.has_carpet
        };

        Object.entries(checkboxes).forEach(([id, value]) => {
            const checkbox = document.getElementById(id);
            if (checkbox) {
                checkbox.checked = value;
            }
        });
    }

    // Initialize the classroom
    function init() {
        // Initialize form with current settings FIRST
        updateFormValues(state.settings);

        // Initialize COLORS and SETTINGS from state
        Object.assign(COLORS, {
            WALL: state.settings.wall_color,
            FLOOR: state.settings.floor_color,
            DESK: state.settings.desk_color,
            CHAIR: state.settings.chair_color,
            BOARD: state.settings.board_color
        });

        Object.assign(SETTINGS, {
            NUM_ROWS: state.settings.number_of_rows,
            DESKS_PER_ROW: state.settings.desks_per_row,
            HAS_PLANTS: state.settings.has_plants,
            HAS_WINDOWS: state.settings.has_windows,
            HAS_BOOKSHELF: state.settings.has_bookshelf,
            HAS_CLOCK: state.settings.has_clock,
            HAS_CARPET: state.settings.has_carpet
        });

        // Initial render
        renderClassroom();

        // Start character animation loop
        requestAnimationFrame(updateCharacter);
    }

    // DOM elements
    const classroomContainer = document.getElementById('classroomContainer');
    const controlPanel = document.getElementById('controlPanel');
    const toggleControls = document.getElementById('toggleControls');

    // Initialize cached rect and set up resize listener
    refreshContainerRect();
    window.addEventListener('resize', refreshContainerRect);

    // Event listeners for controls
    toggleControls.addEventListener('click', () => {
        controlPanel.classList.toggle('hidden');
        toggleControls.querySelector('span').textContent =
            controlPanel.classList.contains('hidden') ? 'Show Controls' : 'Hide Controls';
    });

    // Color input handlers
    document.querySelectorAll('input[type="color"]').forEach(input => {
        input.addEventListener('input', (e) => {
            const settings = loadSettings();
            const settingKey = e.target.id.replace(/([A-Z])/g, '_$1').toLowerCase();
            settings[settingKey] = e.target.value;
            document.getElementById(`${e.target.id}Value`).textContent = e.target.value;
            state.settings = settings;
            saveSettings(settings);
        });
    });

    // Range input handlers
    document.querySelectorAll('input[type="range"]').forEach(input => {
        input.addEventListener('input', (e) => {
            const settings = loadSettings();
            const settingKey = e.target.id.replace(/([A-Z])/g, '_$1').toLowerCase();
            settings[settingKey] = parseInt(e.target.value);
            document.getElementById(`${e.target.id}Value`).textContent = e.target.value;
            state.settings = settings;
            saveSettings(settings);
        });
    });

    // Checkbox handlers
    document.querySelectorAll('input[type="checkbox"]').forEach(input => {
        input.addEventListener('change', (e) => {
            const settings = loadSettings();
            const settingKey = e.target.id.replace(/([A-Z])/g, '_$1').toLowerCase();
            settings[settingKey] = e.target.checked;
            state.settings = settings;
            saveSettings(settings);
        });
    });

    // Movement handlers
    window.addEventListener('keydown', (e) => {
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            // Only allow movement if not seated
            if (!state.isSeated) {
                state.keysPressed[e.key] = true;
                e.preventDefault();
            }
        }
    });

    window.addEventListener('keyup', (e) => {
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            // Only allow movement if not seated
            if (!state.isSeated) {
                state.keysPressed[e.key] = false;
                e.preventDefault();
            }
        }
    });

    // Initialize WebSocket connection
    const classroomId = document.querySelector('meta[name="classroom-id"]').content;
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const ws_path = `${ws_scheme}://${window.location.host}/ws/classroom/${classroomId}/`;
    let socket = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 3000; // 3 seconds

    function connectWebSocket() {
        socket = new WebSocket(ws_path);

        socket.onopen = function () {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
        };

        socket.onclose = function (e) {
            console.log('WebSocket disconnected');
            if (reconnectAttempts < maxReconnectAttempts) {
                setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    reconnectAttempts++;
                    connectWebSocket();
                }, reconnectDelay);
            }
        };

        socket.onerror = function (error) {
            console.error('WebSocket error:', error);
        };

        socket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            console.log('Received message:', data); // Debug log

            switch (data.type) {
                case 'participants_list':
                    console.log('Processing participants list:', data.participants); // Debug log
                    // Clear all seat labels first
                    document.querySelectorAll('.student-name').forEach(label => {
                        label.classList.add('hidden');
                    });

                    // Clear occupied seats tracking
                    interactionState.occupiedSeats.clear();

                    // Update seats and student list
                    data.participants.forEach(participant => {
                        if (participant.seat_id) {
                            console.log('Setting seat label for participant:', participant.full_name, participant.seat_id); // Debug log
                            updateSeatLabel(participant.seat_id, participant.full_name);
                            markSeatOccupied(participant.seat_id);
                        }
                        // Initialize or update participant data
                        if (!otherParticipants.has(participant.username)) {
                            otherParticipants.set(participant.username, {
                                full_name: participant.full_name,
                                position: { x: 400, y: 300 }, // Default starting position
                                direction: 'down',
                                isMoving: false,
                                walkFrame: 0,
                                seat_id: participant.seat_id
                            });
                        }
                    });

                    updateStudentsList(data.participants)
                    break;

                case 'position_update':
                    // Update position of other participant
                    if (data.username && data.username !== getCurrentUsername()) {
                        if (!otherParticipants.has(data.username)) {
                            otherParticipants.set(data.username, {
                                full_name: data.full_name || data.username,
                                position: data.position || { x: 400, y: 300 },
                                direction: data.direction || 'down',
                                isMoving: data.isMoving || false,
                                walkFrame: 0,
                                seat_id: data.seat_id
                            });
                        } else {
                            const participant = otherParticipants.get(data.username);
                            participant.position = data.position;
                            participant.direction = data.direction;
                            participant.isMoving = data.isMoving;
                        }
                    }
                    break;

                case 'seat_updated':
                    if (data.seat_id) {
                        console.log('Updating seat label:', data.seat_id, data.user.full_name); // Debug log
                        // Wait a bit to ensure the classroom is rendered
                        setTimeout(() => {
                            updateSeatLabel(data.seat_id, data.user.full_name);
                        }, 100);

                        // Mark seat as occupied
                        markSeatOccupied(data.seat_id);

                        // Show notification
                        showNotification(`${data.user.full_name} has taken seat ${data.seat_id}`, 'info');

                        // If this is the current user taking a seat, update their state
                        if (data.user.username === getCurrentUsername()) {
                            state.isSeated = true;
                            state.currentSeat = data.seat_id;
                        } else {
                            // Update other participant's seat
                            if (otherParticipants.has(data.user.username)) {
                                otherParticipants.get(data.user.username).seat_id = data.seat_id;
                            }
                        }
                    }
                    break;

                case 'seat_left':
                    if (data.seat_id) {
                        console.log('User left seat:', data.seat_id, data.user.full_name); // Debug log
                        clearSeatLabel(data.seat_id);

                        // Mark seat as available
                        markSeatAvailable(data.seat_id);

                        // Show notification
                        showNotification(`${data.user.full_name} has left seat ${data.seat_id}`, 'info');

                        // If this is the current user leaving a seat, update their state
                        if (data.user.username === getCurrentUsername()) {
                            state.isSeated = false;
                            state.currentSeat = null;
                        } else {
                            // Update other participant's seat
                            if (otherParticipants.has(data.user.username)) {
                                otherParticipants.get(data.user.username).seat_id = null;
                            }
                        }
                    }
                    break;

                case 'participant_left':
                    // Use a safer approach to find the participant element
                    const participants = document.querySelectorAll('[data-username]');
                    const participant = Array.from(participants).find(el =>
                        el.getAttribute('data-username') === data.user.username
                    );

                    if (participant) {
                        const seatId = participant.querySelector('.text-sm')?.textContent?.replace('Seat: ', '');
                        if (seatId) {
                            clearSeatLabel(seatId);
                            markSeatAvailable(seatId);
                        }
                    }
                    removeStudent(data.user);
                    otherParticipants.delete(data.user.username);

                    // Show notification
                    showNotification(`${data.user.full_name} has left the classroom`, 'info');
                    break;

                case 'participant_joined':
                    addStudent(data.user, data.seat_id);
                    if (data.seat_id) {
                        updateSeatLabel(data.seat_id, data.user.full_name);
                        markSeatOccupied(data.seat_id);
                    }
                    // Initialize participant data
                    if (!otherParticipants.has(data.user.username)) {
                        otherParticipants.set(data.user.username, {
                            full_name: data.user.full_name,
                            position: { x: 400, y: 300 },
                            direction: 'down',
                            isMoving: false,
                            walkFrame: 0,
                            seat_id: data.seat_id
                        });
                    }

                    // Show notification
                    showNotification(`${data.user.full_name} has joined the classroom`, 'success');
                    break;

                case 'seat_occupied':
                    console.log('Seat is occupied:', data.seat_id); // Debug log
                    showNotification(data.message || 'This seat is already taken by another student.', 'warning');
                    // Reset user's seated state since they couldn't take the seat
                    state.isSeated = false;
                    state.currentSeat = null;
                    break;
            }
        };
    }

    // Connect WebSocket
    connectWebSocket();

    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && (!socket || socket.readyState === WebSocket.CLOSED)) {
            connectWebSocket();
        }
    });

    // Add function to update seat labels
    function updateSeatLabel(seatId, studentName) {
        console.log('Updating seat label for:', seatId, studentName); // Debug log

        const nameLabel = document.querySelector(`[data-seat-id="${seatId}"]`);
        console.log('Found name label:', nameLabel); // Debug log

        if (nameLabel) {
            nameLabel.textContent = studentName;
            nameLabel.classList.remove('hidden');
            console.log('Successfully updated seat label:', seatId, studentName); // Debug log
        } else {
            console.error('Name label not found for seat:', seatId);
            // List all available name labels for debugging
            const allLabels = document.querySelectorAll('[data-seat-id]');
            console.log('Available name labels:', Array.from(allLabels).map(el => el.getAttribute('data-seat-id')));
        }
    }

    // Add function to clear seat label
    function clearSeatLabel(seatId) {
        const nameLabel = document.querySelector(`[data-seat-id="${seatId}"]`);
        if (nameLabel) {
            nameLabel.textContent = '';
            nameLabel.classList.add('hidden');
        }
    }

    // Student list management functions
    function updateStudentsList(participants) {
        const studentsList = document.getElementById('studentsList');
        if (studentsList) {
            studentsList.innerHTML = '';
            participants.forEach(participant => {
                addStudent(participant, participant.seat_id);
            });
            updateParticipantCount(participants.length);
        }
    }

    function addStudent(user, seatId) {
        const studentsList = document.getElementById('studentsList');
        if (!studentsList) return;

        const studentElement = document.createElement('div');
        studentElement.className = 'flex items-center space-x-3 p-3 bg-white rounded-lg shadow-sm border border-gray-100 mb-2';
        studentElement.setAttribute('data-username', user.username);

        // Create avatar container
        const avatarContainer = document.createElement('div');
        avatarContainer.className = 'flex-shrink-0';

        const avatar = document.createElement('div');
        avatar.className = 'h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center';

        const avatarText = document.createElement('span');
        avatarText.className = 'text-blue-600 font-medium';
        avatarText.textContent = user.full_name.charAt(0); // Safe: textContent escapes HTML

        avatar.appendChild(avatarText);
        avatarContainer.appendChild(avatar);

        // Create info container
        const infoContainer = document.createElement('div');
        infoContainer.className = 'flex-1';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'text-gray-900';
        nameSpan.textContent = user.full_name; // Safe: textContent escapes HTML

        infoContainer.appendChild(nameSpan);

        if (seatId) {
            const seatSpan = document.createElement('span');
            seatSpan.className = 'text-sm text-gray-500 block';
            seatSpan.textContent = `Seat: ${seatId}`; // Safe: textContent escapes HTML
            infoContainer.appendChild(seatSpan);
        }

        studentElement.appendChild(avatarContainer);
        studentElement.appendChild(infoContainer);
        studentsList.appendChild(studentElement);
    }

    function removeStudent(user) {
        const studentsList = document.getElementById('studentsList');
        if (!studentsList) return;

        // Use a safer approach to find the student element
        const students = studentsList.querySelectorAll('[data-username]');
        const studentElement = Array.from(students).find(el =>
            el.getAttribute('data-username') === user.username
        );

        if (studentElement) {
            studentElement.remove();
        }
    }

    function updateParticipantCount(count) {
        const countElement = document.querySelector('#participantCount');
        if (countElement) {
            countElement.textContent = count;
        }
    }

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        let bgColorClass;

        switch (type) {
            case 'warning':
                bgColorClass = 'bg-yellow-600';
                break;
            case 'error':
                bgColorClass = 'bg-red-600';
                break;
            case 'success':
                bgColorClass = 'bg-green-600';
                break;
            default:
                bgColorClass = 'bg-blue-600';
        }

        notification.className = `fixed bottom-4 right-4 ${bgColorClass} text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 opacity-0`;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Fade in
        setTimeout(() => {
            notification.classList.remove('opacity-0');
        }, 100);

        // Fade out and remove
        setTimeout(() => {
            notification.classList.add('opacity-0');
            setTimeout(() => {
                notification.remove();
            }, 500);
        }, 3000);
    }

    // Rendering functions
    function renderClassroom() {
        classroomContainer.innerHTML = '';
        renderWalls();
        renderFloor();
        renderCarpet();
        renderTeacherDesk();
        renderDesksAndChairs();
        renderWhiteboard();
        renderWindows();
        renderBookshelf();
        renderClock();
        renderPlants();
        renderDoor();
        renderCharacter();
    }

    function renderWalls() {
        const frontWall = document.createElement('div');
        frontWall.className = 'absolute transition-colors duration-300';
        frontWall.style.cssText = `
            width: 100%;
            height: 39%;
            background-color: ${state.settings.wall_color};
            top: 0;
            left: 0;
            z-index: 1;
            border-bottom: 6px solid #a0a0a0;
        `;
        classroomContainer.appendChild(frontWall);

        const sideWall1 = document.createElement('div');
        sideWall1.className = 'absolute transition-colors duration-300';
        sideWall1.style.cssText = `
            width: 15%;
            height: 39%;
            background-color: ${darkenColor(state.settings.wall_color, 20)};
            top: 0;
            right: 0;
            z-index: 2;
            border-left: 6px solid #a0a0a0;
            border-bottom: 6px solid #a0a0a0;
        `;
        classroomContainer.appendChild(sideWall1);
        const sideWall2 = document.createElement('div');
        sideWall2.className = 'absolute transition-colors duration-300';
        sideWall2.style.cssText = `
            width: 15%;
            height: 39%;
            background-color: ${darkenColor(state.settings.wall_color, 20)};
            top: 0;
            left: 0;
            z-index: 2;
            border-left: 6px solid #a0a0a0;
            border-bottom: 6px solid #a0a0a0;
        `;
        classroomContainer.appendChild(sideWall2);
    }

    function renderFloor() {
        const floor = document.createElement('div');
        floor.className = 'absolute transition-colors duration-300';
        floor.style.cssText = `
            width: 100%;
            height: 60%;
            background-color: ${state.settings.floor_color};
            bottom: 0;
            left: 0;
            z-index: 3;
            transform: perspective(1000px) rotateX(30deg);
            transform-origin: bottom;
            background-image: linear-gradient(90deg, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.1) 1%, rgba(0,0,0,0) 1%, rgba(0,0,0,0) 100%), linear-gradient(rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.1) 1%, rgba(0,0,0,0) 1%, rgba(0,0,0,0) 100%);
            background-size: 40px 40px;
        `;
        classroomContainer.appendChild(floor);
    }

    function renderCarpet() {
        if (!state.settings.has_carpet) return;

        const carpet = document.createElement('div');
        carpet.className = 'absolute rounded-lg transition-all duration-300';
        carpet.style.cssText = `
            width: 65%;
            height: 18%;
            background-color: #8B008B;
            opacity: 0.15;
            left: 17.5%;
            top: 40%;
            z-index: 5;
            background-image: repeating-linear-gradient(45deg, rgba(255,255,255,0.1) 0, rgba(255,255,255,0.1) 10px, transparent 10px, transparent 20px);
            transform: perspective(1000px) rotateX(30deg);
            transform-origin: center top;
        `;
        classroomContainer.appendChild(carpet);
    }

    function renderTeacherDesk() {
        const desk = document.createElement('div');
        desk.className = 'absolute transition-colors duration-300 shadow-lg';
        desk.style.cssText = `
            width: 140px;
            height: 70px;
            background-color: ${darkenColor(state.settings.desk_color, 10)};
            left: 10%;
            top: 30%;
            z-index: 8;
            transform: perspective(500px) rotateX(30deg);
            border-radius: 3px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        `;

        // Store teacher's desk position for interaction
        interactionState.interactiveElements.teacherDesk = {
            x: classroomContainer.clientWidth * 0.1,
            y: classroomContainer.clientHeight * 0.3,
            width: 140,
            height: 70
        };

        // Desk items
        const paper = document.createElement('div');
        paper.className = 'absolute top-2 left-4 w-8 h-10 bg-white rounded-sm shadow-sm transform rotate-10';
        desk.appendChild(paper);

        const apple = document.createElement('div');
        apple.className = 'absolute top-4 left-14 w-6 h-6 bg-red-600 rounded-full shadow-sm';
        desk.appendChild(apple);

        const pen = document.createElement('div');
        pen.className = 'absolute top-3 right-4 w-4 h-8 bg-blue-800 rounded-sm shadow-sm';
        desk.appendChild(pen);

        // Desk legs
        ['left-4', 'right-4', 'left-20', 'right-20'].forEach(position => {
            const leg = document.createElement('div');
            leg.className = `absolute bottom-0 ${position} w-3 h-12 bg-gray-800`;
            leg.style.transform = 'translateY(100%)';
            desk.appendChild(leg);
        });

        classroomContainer.appendChild(desk);
    }

    function renderDesksAndChairs() {
        const { number_of_rows, desks_per_row } = state.settings;
        const roomWidth = classroomContainer.clientWidth * 0.8;
        const roomDepth = classroomContainer.clientHeight * 0.8;

        const startX = classroomContainer.clientWidth * 0.1;
        const startY = classroomContainer.clientHeight * 0.5;

        const deskWidth = Math.min(80, roomWidth / desks_per_row);
        const deskDepth = Math.min(60, roomDepth / number_of_rows);

        const spacingX = roomWidth / desks_per_row;
        const spacingY = roomDepth / number_of_rows;

        // Clear previous seats array
        interactionState.interactiveElements.seats = [];

        for (let row = 0; row < number_of_rows; row++) {
            for (let col = 0; col < desks_per_row; col++) {
                const x = startX + col * spacingX;
                const y = startY + row * spacingY * 0.6;

                // Store seat position for interaction
                interactionState.interactiveElements.seats.push({
                    id: `seat-${row}-${col}`,
                    x: x,
                    y: y + deskDepth,
                    width: deskWidth * 0.6,
                    height: deskDepth * 0.5
                });

                // Create desk-chair set container
                const deskChairSet = document.createElement('div');
                deskChairSet.className = 'desk-chair-set absolute';
                deskChairSet.id = `desk-chair-${row}-${col}`;
                deskChairSet.style.cssText = `left: ${x}px; top: ${y}px;`;

                // Create desk
                const desk = document.createElement('div');
                desk.className = 'absolute transition-colors duration-300 shadow-md';
                desk.style.cssText = `
                    width: ${deskWidth}px;
                    height: ${deskDepth}px;
                    background-color: ${state.settings.desk_color};
                    transform: perspective(500px) rotateX(30deg);
                    z-index: ${10 + (number_of_rows - row)};
                    border-radius: 2px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                `;

                // Add desk legs
                ['left-2', 'right-2'].forEach(position => {
                    const leg = document.createElement('div');
                    leg.className = `absolute bottom-0 ${position} w-2 h-10 bg-gray-700`;
                    leg.style.transform = 'translateY(100%)';
                    desk.appendChild(leg);
                });

                // Create chair
                const chair = document.createElement('div');
                chair.className = 'absolute transition-colors duration-300 shadow-md';
                chair.style.cssText = `
                    width: ${deskWidth * 0.6}px;
                    height: ${deskDepth * 0.5}px;
                    background-color: ${state.settings.chair_color};
                    top: ${deskDepth + 5}px;
                    left: ${deskWidth * 0.2}px;
                    z-index: ${10 + (number_of_rows - row) - 1};
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border-bottom-left-radius: 3px;
                    border-bottom-right-radius: 3px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                `;

                // Add chair back
                const chairBack = document.createElement('div');
                chairBack.className = 'absolute top-0 left-0 right-0 h-8 bg-gray-800';
                chairBack.style.cssText = `
                    transform: translateY(-80%);
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                `;
                chair.appendChild(chairBack);

                // Add student name label (hidden by default)
                const nameLabel = document.createElement('div');
                nameLabel.className = 'student-name absolute text-white text-sm font-bold bg-gray-800 bg-opacity-90 px-3 py-2 rounded-lg hidden';
                nameLabel.setAttribute('data-seat-id', `seat-${row}-${col}`);
                nameLabel.style.cssText = `
                    left: ${x + (deskWidth * 0.5)}px;
                    top: ${y + deskDepth - 20}px;
                    transform: translateX(-50%);
                    white-space: nowrap;
                    z-index: 10000;
                    pointer-events: none;
                    border: 2px solid rgba(255, 255, 255, 0.5);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
                    backdrop-filter: blur(2px);
                `;

                // Append to classroom container instead of chair
                classroomContainer.appendChild(nameLabel);

                deskChairSet.appendChild(desk);
                deskChairSet.appendChild(chair);
                classroomContainer.appendChild(deskChairSet);
            }
        }
    }

    function renderWhiteboard() {
        const boardContainer = document.createElement('div');
        boardContainer.className = 'absolute';
        boardContainer.style.cssText = `
            z-index: 10;
            top: 7%;
            width: 100%;
        `;

        const board = document.createElement('div');
        board.className = 'mx-auto transition-colors duration-300 shadow-lg relative';
        board.style.cssText = `
            width: 65%;
            height: ${classroomContainer.clientHeight * 0.2}px;
            background-color: ${state.settings.board_color};
            border: 12px solid #6b4226;
            border-radius: 4px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        `;

        // Store blackboard position for interaction
        const boardRect = {
            x: classroomContainer.clientWidth * 0.175,
            y: classroomContainer.clientHeight * 0.07,
            width: classroomContainer.clientWidth * 0.65,
            height: classroomContainer.clientHeight * 0.2
        };
        interactionState.interactiveElements.blackboard = boardRect;

        const text = document.createElement('div');
        text.className = 'text-white text-center h-full flex items-center justify-center text-xl font-bold';
        text.textContent = 'Virtual Classroom';
        board.appendChild(text);

        const ledge = document.createElement('div');
        ledge.className = 'absolute -bottom-4 left-0 right-0 h-4 bg-[#8B4513]';
        ledge.style.cssText = `
            transform: perspective(100px) rotateX(45deg);
            transform-origin: top;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        `;
        board.appendChild(ledge);

        boardContainer.appendChild(board);
        classroomContainer.appendChild(boardContainer);
    }

    function renderWindows() {
        if (!state.settings.has_windows) return;

        // Side wall window
        const sideWindow = document.createElement('div');
        sideWindow.className = 'absolute rounded-lg shadow-inner transition-all duration-300 flex items-center justify-center';
        sideWindow.style.cssText = `
            width: 60px;
            height: 100px;
            background-color: #87CEEB;
            right: 1.5%;
            top: 10%;
            z-index: 5;
            border: 8px solid #A0522D;
            box-shadow: inset 0 0 20px rgba(255,255,255,0.5);
            background-image: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 50%, rgba(255,255,255,0.4) 100%);
        `;
        const windIcon1 = document.createElement('i');
        windIcon1.setAttribute('data-lucide', 'wind');
        windIcon1.className = 'text-white opacity-70';
        sideWindow.appendChild(windIcon1);
        classroomContainer.appendChild(sideWindow);

        // Front wall windows
        [30, 55].forEach(leftPos => {
            const frontWindow = document.createElement('div');
            frontWindow.className = 'absolute rounded-lg shadow-inner transition-all duration-300 flex items-center justify-center';
            frontWindow.style.cssText = `
                width: 80px;
                height: 120px;
                background-color: #87CEEB;
                left: ${leftPos}%;
                top: 12%;
                z-index: 5;
                border: 8px solid #A0522D;
                box-shadow: inset 0 0 20px rgba(255,255,255,0.5);
                background-image: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 50%, rgba(255,255,255,0.4) 100%);
            `;
            const windIcon = document.createElement('i');
            windIcon.setAttribute('data-lucide', 'wind');
            windIcon.className = 'text-white opacity-70';
            frontWindow.appendChild(windIcon);
            classroomContainer.appendChild(frontWindow);
        });

        // Reinitialize Lucide icons for the new wind icons
        lucide.createIcons();
    }

    function renderBookshelf() {
        if (!state.settings.has_bookshelf) return;

        const bookshelf = document.createElement('div');
        bookshelf.className = 'absolute';
        bookshelf.style.cssText = `
            right: 6%;
            top: 24%;
            width: 100px;
            height: 150px;
            z-index: 7;
        `;

        // Create bookshelf HTML structure (non-interactive)
        bookshelf.innerHTML = `
            <div class="relative w-full h-full bg-[#8B4513] rounded-sm shadow-lg">
                <div class="absolute top-0 left-0 w-full h-1/3 border-b-2 border-[#6b4226] flex justify-around items-center px-2">
                    <div class="w-4 h-12 bg-red-800"></div>
                    <div class="w-4 h-12 bg-blue-800"></div>
                    <div class="w-4 h-12 bg-green-800"></div>
                </div>
                <div class="absolute top-1/3 left-0 w-full h-1/3 border-b-2 border-[#6b4226] flex justify-around items-center px-2">
                    <div class="w-4 h-12 bg-yellow-800"></div>
                    <div class="w-4 h-12 bg-purple-800"></div>
                    <div class="w-4 h-12 bg-orange-800"></div>
                </div>
                <div class="absolute top-2/3 left-0 w-full h-1/3 flex justify-around items-center px-2">
                    <div class="w-4 h-12 bg-pink-800"></div>
                    <div class="w-4 h-12 bg-indigo-800"></div>
                    <div class="w-4 h-12 bg-teal-800"></div>
                </div>
            </div>
        `;

        classroomContainer.appendChild(bookshelf);
    }

    function renderClock() {
        if (!state.settings.has_clock) return;

        const clock = document.createElement('div');
        clock.className = 'absolute flex items-center justify-center rounded-full shadow-md transition-all duration-300';
        clock.style.cssText = `
            width: 60px;
            height: 60px;
            background-color: #F5F5F5;
            border: 3px solid #333;
            right: 8%;
            top: 13%;
            z-index: 20;
        `;

        const clockIcon = document.createElement('i');
        clockIcon.setAttribute('data-lucide', 'clock');
        clockIcon.className = 'text-gray-800';
        clockIcon.style.width = '40px';
        clockIcon.style.height = '40px';
        clock.appendChild(clockIcon);

        classroomContainer.appendChild(clock);
        lucide.createIcons();
    }

    function renderPlants() {
        if (!state.settings.has_plants) return;

        // Corner plant
        const cornerPlant = document.createElement('div');
        cornerPlant.className = 'absolute transition-all duration-300';
        cornerPlant.style.cssText = `
            right: 10%;
            top: 48%;
            z-index: 16;
        `;
        cornerPlant.innerHTML = `
            <div class="w-16 h-28 flex flex-col items-center">
                <div class="w-12 h-14 bg-green-700 rounded-full -mb-3 z-10"></div>
                <div class="w-14 h-14 bg-green-600 rounded-full -mb-3 z-20"></div>
                <div class="w-16 h-16 bg-green-500 rounded-full -mb-2 z-30"></div>
                <div class="w-8 h-12 bg-amber-700 rounded-md z-0"></div>
            </div>
        `;
        classroomContainer.appendChild(cornerPlant);

        // Front wall plant
        const frontPlant = document.createElement('div');
        frontPlant.className = 'absolute transition-all duration-300';
        frontPlant.style.cssText = `
            right: 0%;
            top: 31.25%;
            z-index: 16;
        `;
        frontPlant.innerHTML = `
            <div class="w-20 h-32 flex flex-col items-center">
                <div class="w-16 h-18 bg-green-600 rounded-full -mb-3 z-10"></div>
                <div class="w-18 h-18 bg-green-500 rounded-full -mb-3 z-20"></div>
                <div class="w-16 h-16 bg-green-400 rounded-full -mb-2 z-30"></div>
                <div class="w-10 h-14 bg-amber-800 rounded-md z-0"></div>
            </div>
        `;
        classroomContainer.appendChild(frontPlant);
    }

    function renderDoor() {
        const door = document.createElement('div');
        door.className = 'absolute transition-all duration-300';
        door.style.cssText = `
            width: 60px;
            height: 120px;
            background-color: #8B4513;
            left: 3%;
            top: 24%;
            z-index: 6;
            border-left: 5px solid #6b4226;
            border-top: 5px solid #6b4226;
            border-bottom: 5px solid #6b4226;
            border-top-left-radius: 5px;
            border-bottom-left-radius: 5px;
        `;

        const doorHandle = document.createElement('div');
        doorHandle.className = 'absolute right-3 top-1/2 w-3 h-3 bg-yellow-600 rounded-full';
        door.appendChild(doorHandle);

        classroomContainer.appendChild(door);
    }

    function renderCharacter() {
        // Remove any existing character first
        const existingCharacter = classroomContainer.querySelector('.character-facing-up, .character-facing-down, .character-facing-left, .character-facing-right');
        if (existingCharacter) {
            existingCharacter.remove();
        }

        // Don't render character if seated
        if (state.isSeated) {
            return;
        }

        const character = document.createElement('div');
        character.className = `absolute transition-transform duration-200 pointer-events-none character-facing-${state.character.direction}`;
        character.setAttribute('data-player-type', 'current');
        character.style.cssText = `
            left: ${state.character.position.x}px;
            top: ${state.character.position.y}px;
            transform: translate(-50%, -50%);
            z-index: ${Math.floor(state.character.position.y)};
        `;

        // Character design HTML
        character.innerHTML = `
            <div class="relative">
                <div class="flex flex-col items-center">
                    <div class="w-16 h-16 relative">
                        <div class="absolute w-14 h-14 bg-[#FFD9B3] rounded-full top-1 left-1 shadow-md border border-[#E0B088]"></div>
                        ${getCharacterHairHTML()}
                        ${getCharacterFaceHTML()}
                    </div>
                    ${getCharacterBodyHTML()}
                </div>
            </div>
        `;

        classroomContainer.appendChild(character);
    }

    function renderOtherParticipants() {
        // Remove existing other participant characters
        document.querySelectorAll('[data-player-type="other"]').forEach(el => el.remove());

        // Render each other participant
        otherParticipants.forEach((participantData, username) => {
            if (participantData.seat_id) {
                // Don't render if seated - their name will show on the seat
                return;
            }

            const character = document.createElement('div');
            character.className = `absolute transition-transform duration-200 pointer-events-none character-facing-${participantData.direction}`;
            character.setAttribute('data-player-type', 'other');
            character.setAttribute('data-username', username);
            character.style.cssText = `
                left: ${participantData.position.x}px;
                top: ${participantData.position.y}px;
                transform: translate(-50%, -50%);
                z-index: ${Math.floor(participantData.position.y)};
            `;

            // Use a different color for other participants (teal instead of blue)
            const bodyColor = '#14B8A6'; // teal-500
            character.innerHTML = `
                <div class="relative">
                    <div class="flex flex-col items-center">
                        <div class="w-16 h-16 relative">
                            <div class="absolute w-14 h-14 bg-[#FFD9B3] rounded-full top-1 left-1 shadow-md border border-[#E0B088]"></div>
                            ${getCharacterHairHTMLForOther()}
                            ${getCharacterFaceHTMLForOther()}
                        </div>
                        <div class="relative w-20 h-24 -mt-4">
                            <div class="w-16 h-16 bg-teal-500 rounded-md mx-auto" style="background-color: ${bodyColor}">
                            </div>
                            ${getCharacterArmsHTMLForOther(participantData.walkFrame)}
                            ${getCharacterLegsHTMLForOther(participantData.isMoving, participantData.walkFrame)}
                            <div class="absolute bottom-0 w-16 h-12 bg-black opacity-30 -z-10 rounded-md transform translate-y-[-3px] translate-x-[9px]"></div>
                        </div>
                    </div>
                </div>
            `;

            // Add name label above the character
            const nameLabel = document.createElement('div');
            nameLabel.className = 'absolute text-white text-xs font-bold bg-gray-800 bg-opacity-90 px-2 py-1 rounded whitespace-nowrap';
            nameLabel.style.cssText = `
                left: ${participantData.position.x}px;
                top: ${participantData.position.y - 60}px;
                transform: translateX(-50%);
                z-index: ${Math.floor(participantData.position.y) + 1};
                pointer-events: none;
                border: 1px solid rgba(255, 255, 255, 0.3);
            `;
            nameLabel.textContent = participantData.full_name;

            classroomContainer.appendChild(nameLabel);
            classroomContainer.appendChild(character);
        });
    }

    function getCharacterHairHTMLForOther() {
        return '<div class="absolute w-14 h-7 bg-[#8B4513] rounded-t-full top-0 left-1"></div>';
    }

    function getCharacterFaceHTMLForOther() {
        return `
            <div class="absolute top-6 left-4 w-2 h-2 bg-[#302825] rounded-full"></div>
            <div class="absolute top-6 right-4 w-2 h-2 bg-[#302825] rounded-full"></div>
            <div class="absolute top-10 left-6 w-4 h-1 bg-[#CC6666] rounded-full"></div>
        `;
    }

    function getCharacterArmsHTMLForOther(walkFrame) {
        return `
            <div class="absolute left-0 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? 'rotate-6' : '-rotate-6'}"></div>
            <div class="absolute right-0 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? '-rotate-6' : 'rotate-6'}"></div>
        `;
    }

    function getCharacterLegsHTMLForOther(isMoving, walkFrame) {
        return `
            <div class="absolute bottom-0 left-4 w-12 h-2 bg-transparent flex justify-between">
                <div class="w-4 h-10 bg-[#1F456E] rounded-md transform origin-top ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-0' : 'translate-y-1') : ''
            }"></div>
                <div class="w-4 h-10 bg-[#1F456E] rounded-md transform origin-top ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-1' : 'translate-y-0') : ''
            }"></div>
            </div>
            <div class="absolute bottom-0 left-3 w-14 h-2 bg-transparent flex justify-between">
                <div class="w-5 h-3 bg-[#222] rounded-md transform ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-0' : 'translate-y-1') : ''
            }"></div>
                <div class="w-5 h-3 bg-[#222] rounded-md transform ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-1' : 'translate-y-0') : ''
            }"></div>
            </div>
        `;
    }

    // Helper functions for character rendering
    function getCharacterHairHTML() {
        switch (state.character.direction) {
            case 'down':
                return '<div class="absolute w-14 h-7 bg-[#8B4513] rounded-t-full top-0 left-1"></div>';
            case 'up':
                return '<div class="absolute w-14 h-8 bg-[#8B4513] rounded-t-full top-0 left-1"></div>';
            case 'left':
                return `
                    <div class="absolute w-14 h-7 bg-[#8B4513] rounded-t-full top-0 left-1"></div>
                `;
            case 'right':
                return `
                    <div class="absolute w-14 h-7 bg-[#8B4513] rounded-t-full top-0 left-1"></div>
                `;
            default:
                return '';
        }
    }

    function getCharacterFaceHTML() {
        switch (state.character.direction) {
            case 'down':
                return `
                    <div class="absolute top-6 left-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-6 right-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-10 left-6 w-4 h-1 bg-[#CC6666] rounded-full"></div>
                `;
            case 'up':
                return '<div class="absolute top-3 left-3 w-8 h-2 bg-[#8B4513] rounded-full"></div>';
            case 'left':
                return `
                    <div class="absolute top-6 left-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-10 left-3 w-2 h-1 bg-[#CC6666] rounded-full"></div>
                `;
            case 'right':
                return `
                    <div class="absolute top-6 right-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-10 right-3 w-2 h-1 bg-[#CC6666] rounded-full"></div>
                `;
            default:
                return '';
        }
    }

    function getCharacterBodyHTML() {
        const isMoving = state.character.isMoving;
        const walkFrame = state.character.walkFrame;

        return `
            <div class="relative w-20 h-24 -mt-4">
                <div class="w-16 h-16 bg-blue-600 rounded-md mx-auto ${isMoving ? 'animate-pulse' : ''}"
                     style="background-color: ${isMoving ? '#4169E1' : '#3457D1'}">
                </div>
                ${getCharacterArmsHTML()}
                ${getCharacterLegsHTML()}
                <div class="absolute bottom-0 w-16 h-12 bg-black opacity-30 -z-10 rounded-md transform translate-y-[-3px] translate-x-[9px]"></div>
            </div>
        `;
    }

    function getCharacterArmsHTML() {
        const walkFrame = state.character.walkFrame;
        switch (state.character.direction) {
            case 'down':
            case 'up':
                return `
                    <div class="absolute left-0 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? 'rotate-6' : '-rotate-6'}"></div>
                    <div class="absolute right-0 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? '-rotate-6' : 'rotate-6'}"></div>
                `;
            case 'left':
                return `<div class="absolute left-1 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? "translate-y-1" : "-translate-y-1"}"></div>`;
            case 'right':
                return `<div class="absolute right-1 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? "translate-y-1" : "-translate-y-1"}"></div>`;
            default:
                return '';
        }
    }

    function getCharacterLegsHTML() {
        const isMoving = state.character.isMoving;
        const walkFrame = state.character.walkFrame;

        return `
            <div class="absolute bottom-0 left-4 w-12 h-2 bg-transparent flex justify-between">
                <div class="w-4 h-10 bg-[#1F456E] rounded-md transform origin-top ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-0' : 'translate-y-1') : ''
            }"></div>
                <div class="w-4 h-10 bg-[#1F456E] rounded-md transform origin-top ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-1' : 'translate-y-0') : ''
            }"></div>
            </div>
            <div class="absolute bottom-0 left-3 w-14 h-2 bg-transparent flex justify-between">
                <div class="w-5 h-3 bg-[#222] rounded-md transform ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-0' : 'translate-y-1') : ''
            }"></div>
                <div class="w-5 h-3 bg-[#222] rounded-md transform ${isMoving ? (walkFrame % 2 === 0 ? 'translate-y-1' : 'translate-y-0') : ''
            }"></div>
            </div>
        `;
    }

    // Track last position update time to avoid spamming WebSocket
    let lastPositionUpdateTime = Date.now();
    const positionUpdateInterval = 100; // Send updates every 100ms

    // Character animation loop
    function updateCharacter() {
        const now = Date.now();
        const deltaTime = (now - state.lastUpdateTime) / 16.67;
        state.lastUpdateTime = now;

        const friction = 0.85;
        const acceleration = 0.8;
        let newVx = state.character.velocity.x;
        let newVy = state.character.velocity.y;

        if (state.keysPressed.ArrowUp) {
            newVy -= acceleration;
            state.character.direction = 'up';
        }
        if (state.keysPressed.ArrowDown) {
            newVy += acceleration;
            state.character.direction = 'down';
        }
        if (state.keysPressed.ArrowLeft) {
            newVx -= acceleration;
            state.character.direction = 'left';
        }
        if (state.keysPressed.ArrowRight) {
            newVx += acceleration;
            state.character.direction = 'right';
        }

        newVx *= friction;
        newVy *= friction;

        // Use cached rect instead of querying getBoundingClientRect every frame
        const containerRect = cachedRect;
        const paddingX = 40;
        const paddingY = 40;

        let newX = state.character.position.x + newVx * deltaTime;
        let newY = state.character.position.y + newVy * deltaTime;

        if (newX < paddingX) {
            newX = paddingX;
            newVx = 0;
        }
        if (newX > containerRect.width - paddingX) {
            newX = containerRect.width - paddingX;
            newVx = 0;
        }
        if (newY < paddingY) {
            newY = paddingY;
            newVy = 0;
        }
        if (newY > containerRect.height - paddingY) {
            newY = containerRect.height - paddingY;
            newVy = 0;
        }

        state.character.isMoving = Math.abs(newVx) > 0.1 || Math.abs(newVy) > 0.1;

        if (state.character.isMoving && now % 150 < 30) {
            state.character.walkFrame = (state.character.walkFrame + 1) % 4;
        } else if (!state.character.isMoving) {
            state.character.walkFrame = 0;
        }

        state.character.position = { x: newX, y: newY };
        state.character.velocity = { x: newVx, y: newVy };

        // Send position update to other users periodically
        if (now - lastPositionUpdateTime > positionUpdateInterval && !state.isSeated) {
            lastPositionUpdateTime = now;
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'position_update',
                    position: { x: newX, y: newY },
                    direction: state.character.direction,
                    isMoving: state.character.isMoving
                }));
            }
        }

        // Check for interactions
        let nearInteractive = false;
        let currentInteractive = null;

        // Check blackboard
        if (isNearInteractive(
            state.character.position.x,
            state.character.position.y,
            interactionState.interactiveElements.blackboard
        )) {
            nearInteractive = true;
            currentInteractive = 'blackboard';
        }

        // Check teacher's desk
        if (isNearInteractive(
            state.character.position.x,
            state.character.position.y,
            interactionState.interactiveElements.teacherDesk
        )) {
            nearInteractive = true;
            currentInteractive = 'teacherDesk';
        }

        // Check seats
        for (const seat of interactionState.interactiveElements.seats) {
            if (isNearInteractive(
                state.character.position.x,
                state.character.position.y,
                seat
            )) {
                nearInteractive = true;
                currentInteractive = seat.id;
                break;
            }
        }

        // Update interaction state and popup
        interactionState.nearInteractive = nearInteractive;
        interactionState.currentInteractive = currentInteractive;

        if (nearInteractive) {
            let message;
            if (currentInteractive && currentInteractive.startsWith('seat-')) {
                if (state.isSeated && state.currentSeat === currentInteractive) {
                    message = 'Press E to stand up';
                } else if (state.isSeated) {
                    message = 'Stand up first to change seats';
                } else {
                    message = 'Press E to sit down';
                }
            } else {
                if (state.isSeated) {
                    message = 'Stand up first to interact with other elements';
                } else {
                    message = 'Press E to interact';
                }
            }
            showInteractionPopup(message);
        } else {
            hideInteractionPopup();
        }

        // Update walk frames for other participants
        otherParticipants.forEach(participant => {
            if (participant.isMoving && now % 150 < 30) {
                participant.walkFrame = (participant.walkFrame + 1) % 4;
            } else if (!participant.isMoving) {
                participant.walkFrame = 0;
            }
        });

        renderCharacter();
        renderOtherParticipants();
        requestAnimationFrame(updateCharacter);
    }

    // Get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Function to get current username (you may need to adjust this based on how you store user info)
    function getCurrentUsername() {
        // This should return the current user's username
        // You might need to add this as a meta tag or global variable
        const userMeta = document.querySelector('meta[name="current-user"]');
        return userMeta ? userMeta.content : null;
    }

    // Function to check if a seat is occupied
    function isSeatOccupied(seatId) {
        return interactionState.occupiedSeats.has(seatId);
    }

    // Function to mark a seat as occupied
    function markSeatOccupied(seatId) {
        interactionState.occupiedSeats.add(seatId);
    }

    // Function to mark a seat as available
    function markSeatAvailable(seatId) {
        interactionState.occupiedSeats.delete(seatId);
    }

    // Call init directly
    init();
});
