/**
 * Photo Capture Modal for Avatar
 * Handles the UI for capturing photos using the camera
 */
const PhotoCaptureModal = (function() {
    'use strict';

    let modal = null;
    let focusTrapHandler = null;
    let capturedBlob = null;
    let onPhotoAccepted = null;
    let isClosing = false;
    let keydownHandler = null;
    let errorTimeoutId = null;
    let beforeUnloadHandler = null;
    let uploadRetryCount = 0;
    const MAX_UPLOAD_RETRIES = 3;

    // State management
    const STATE = {
        INITIALIZING: 'initializing',
        PREVIEW: 'preview',
        CAPTURED: 'captured',
        UPLOADING: 'uploading',
        ERROR: 'error'
    };

    let currentState = STATE.INITIALIZING;

    /**
     * Create the modal HTML structure
     */
    function createModalHTML() {
        const modalHTML = `
            <div id="photo-capture-modal" class="fixed inset-0 z-50 hidden" role="dialog" aria-modal="true" aria-labelledby="photo-capture-title">
                <!-- Backdrop -->
                <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" id="photo-capture-backdrop"></div>

                <!-- Modal Content -->
                <div class="fixed inset-0 flex items-center justify-center p-4">
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-hidden" role="document">
                        <!-- Header -->
                        <div class="flex items-center justify-between p-4 border-b dark:border-gray-700">
                            <h3 id="photo-capture-title" class="text-lg font-semibold text-gray-900 dark:text-white">
                                <i class="fas fa-camera mr-2"></i>Take Photo
                            </h3>
                            <button type="button" id="photo-capture-close"
                                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                                    aria-label="Close modal">
                                <i class="fas fa-times text-xl"></i>
                            </button>
                        </div>

                        <!-- Body -->
                        <div class="p-4">
                            <!-- Error Message -->
                            <div id="photo-capture-error" class="hidden mb-4 p-3 bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300 text-sm">
                                <i class="fas fa-exclamation-circle mr-2"></i>
                                <span id="photo-capture-error-text"></span>
                            </div>

                            <!-- Loading State -->
                            <div id="photo-capture-loading" class="text-center py-8">
                                <i class="fas fa-spinner fa-spin text-3xl text-teal-600 dark:text-teal-400 mb-3"></i>
                                <p class="text-gray-600 dark:text-gray-400">Initializing camera...</p>
                            </div>

                            <!-- Video Preview Container -->
                            <div id="photo-capture-preview-container" class="hidden">
                                <div class="relative aspect-square bg-black rounded-lg overflow-hidden mb-4">
                                    <!-- Live Video Preview -->
                                    <video id="photo-capture-video"
                                           class="w-full h-full object-cover"
                                           autoplay
                                           playsinline
                                           muted></video>

                                    <!-- Captured Image Preview -->
                                    <canvas id="photo-capture-canvas" class="hidden w-full h-full object-cover absolute inset-0"></canvas>

                                    <!-- Capture Overlay Guide -->
                                    <div id="photo-capture-guide" class="absolute inset-0 flex items-center justify-center pointer-events-none">
                                        <div class="w-48 h-48 border-2 border-white border-dashed rounded-full opacity-50"></div>
                                    </div>
                                </div>

                                <!-- Preview State Controls -->
                                <div id="photo-capture-preview-controls" class="flex justify-center gap-3">
                                    <button type="button" id="photo-capture-btn"
                                            class="px-6 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-colors flex items-center gap-2">
                                        <i class="fas fa-camera"></i>
                                        Capture
                                    </button>
                                    <button type="button" id="photo-capture-cancel-btn"
                                            class="px-6 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors">
                                        Cancel
                                    </button>
                                </div>

                                <!-- Captured State Controls -->
                                <div id="photo-capture-captured-controls" class="hidden flex justify-center gap-3">
                                    <button type="button" id="photo-capture-use-btn"
                                            class="px-6 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-colors flex items-center gap-2">
                                        <i class="fas fa-check"></i>
                                        Use Photo
                                    </button>
                                    <button type="button" id="photo-capture-retake-btn"
                                            class="px-6 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors flex items-center gap-2">
                                        <i class="fas fa-redo"></i>
                                        Retake
                                    </button>
                                </div>

                                <!-- Uploading State -->
                                <div id="photo-capture-uploading" class="hidden text-center py-4">
                                    <i class="fas fa-spinner fa-spin text-2xl text-teal-600 dark:text-teal-400 mb-2"></i>
                                    <p class="text-gray-600 dark:text-gray-400">Uploading photo...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Inject modal into body
        const div = document.createElement('div');
        div.innerHTML = modalHTML;
        document.body.appendChild(div.firstElementChild);

        modal = document.getElementById('photo-capture-modal');
    }

    /**
     * Initialize event listeners
     */
    function initEventListeners() {
        // Close button
        document.getElementById('photo-capture-close').addEventListener('click', close);

        // Backdrop click
        document.getElementById('photo-capture-backdrop').addEventListener('click', close);

        // Cancel button
        document.getElementById('photo-capture-cancel-btn').addEventListener('click', close);

        // Capture button
        document.getElementById('photo-capture-btn').addEventListener('click', capturePhoto);

        // Use photo button
        document.getElementById('photo-capture-use-btn').addEventListener('click', usePhoto);

        // Retake button
        document.getElementById('photo-capture-retake-btn').addEventListener('click', retakePhoto);
    }

    /**
     * Handle keyboard events
     */
    function handleKeyDown(e) {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            close();
        }
    }

    /**
     * Update UI based on state
     */
    function setState(state, errorMessage = null) {
        // Capture previous state BEFORE updating for ERROR state restoration
        const previousState = currentState;
        currentState = state;

        const loading = document.getElementById('photo-capture-loading');
        const previewContainer = document.getElementById('photo-capture-preview-container');
        const error = document.getElementById('photo-capture-error');
        const errorText = document.getElementById('photo-capture-error-text');
        const video = document.getElementById('photo-capture-video');
        const canvas = document.getElementById('photo-capture-canvas');
        const guide = document.getElementById('photo-capture-guide');
        const previewControls = document.getElementById('photo-capture-preview-controls');
        const capturedControls = document.getElementById('photo-capture-captured-controls');
        const uploading = document.getElementById('photo-capture-uploading');

        switch (state) {
            case STATE.INITIALIZING:
                // Hide everything except loading
                loading.classList.remove('hidden');
                previewContainer.classList.add('hidden');
                error.classList.add('hidden');
                break;

            case STATE.PREVIEW:
                // Show live video preview
                loading.classList.add('hidden');
                previewContainer.classList.remove('hidden');
                error.classList.add('hidden');
                video.classList.remove('hidden');
                canvas.classList.add('hidden');
                guide.classList.remove('hidden');
                previewControls.classList.remove('hidden');
                capturedControls.classList.add('hidden');
                uploading.classList.add('hidden');
                break;

            case STATE.CAPTURED:
                // Show captured image
                loading.classList.add('hidden');
                previewContainer.classList.remove('hidden');
                error.classList.add('hidden');
                video.classList.add('hidden');
                canvas.classList.remove('hidden');
                guide.classList.add('hidden');
                previewControls.classList.add('hidden');
                capturedControls.classList.remove('hidden');
                uploading.classList.add('hidden');
                break;

            case STATE.UPLOADING:
                // Show uploading state with captured image
                loading.classList.add('hidden');
                previewContainer.classList.remove('hidden');
                error.classList.add('hidden');
                video.classList.add('hidden');
                canvas.classList.remove('hidden');
                guide.classList.add('hidden');
                previewControls.classList.add('hidden');
                capturedControls.classList.add('hidden');
                uploading.classList.remove('hidden');
                break;

            case STATE.ERROR:
                // Show error while preserving previous UI state
                if (errorMessage) {
                    error.classList.remove('hidden');
                    errorText.textContent = errorMessage;
                }
                // Restore UI based on previous state to avoid flash
                if (previousState === STATE.CAPTURED) {
                    video.classList.add('hidden');
                    canvas.classList.remove('hidden');
                    guide.classList.add('hidden');
                    previewControls.classList.add('hidden');
                    capturedControls.classList.remove('hidden');
                    uploading.classList.add('hidden');
                } else if (previousState === STATE.UPLOADING) {
                    video.classList.add('hidden');
                    canvas.classList.remove('hidden');
                    guide.classList.add('hidden');
                    previewControls.classList.add('hidden');
                    capturedControls.classList.add('hidden');
                    uploading.classList.remove('hidden');
                } else {
                    // Default to preview state
                    video.classList.remove('hidden');
                    canvas.classList.add('hidden');
                    guide.classList.remove('hidden');
                    previewControls.classList.remove('hidden');
                    capturedControls.classList.add('hidden');
                    uploading.classList.add('hidden');
                }
                previewContainer.classList.remove('hidden');
                break;
        }
    }

    /**
     * Open the modal and start camera
     * @param {Function} callback - Called with the captured blob when photo is accepted
     */
    async function open(callback) {
        if (!CameraService.isSupported()) {
            console.warn('PhotoCaptureModal: Camera is not supported on this device or requires HTTPS.');
            return;
        }

        // Prevent opening if already closing
        if (isClosing) {
            return;
        }

        onPhotoAccepted = callback;
        capturedBlob = null;

        // Remove modal if present and attached
        if (modal && document.body.contains(modal)) {
            modal.remove();
            modal = null;
        }

        // Create modal if not present or not attached
        if (!modal || !document.body.contains(modal)) {
            createModalHTML();
            initEventListeners();
        }

        // Add keyboard listener (will be removed on close)
        keydownHandler = handleKeyDown;
        document.addEventListener('keydown', keydownHandler);

        // Add beforeunload handler to cleanup camera on navigation
        beforeUnloadHandler = () => {
            CameraService.stop();
        };
        window.addEventListener('beforeunload', beforeUnloadHandler);

        // Reset retry counter for new session
        uploadRetryCount = 0;

        // Show modal
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';


        // Focus trap - focus the close button
        const closeBtn = document.getElementById('photo-capture-close');
        closeBtn.focus();

        // Add focus trap
        const focusableElements = modal.querySelectorAll(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        focusTrapHandler = (e) => {
            // Handle Escape (already handled by keydownHandler, but ensure it works)
            if (e.key === 'Escape') {
                return; // Let existing handler deal with it
            }
            // Handle Tab
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    // Shift+Tab: if on first element, go to last
                    if (document.activeElement === firstFocusable) {
                        e.preventDefault();
                        lastFocusable.focus();
                    }
                } else {
                    // Tab: if on last element, go to first
                    if (document.activeElement === lastFocusable) {
                        e.preventDefault();
                        firstFocusable.focus();
                    }
                }
            }
        };
        modal.addEventListener('keydown', focusTrapHandler);

        setState(STATE.INITIALIZING);

        try {
            const video = document.getElementById('photo-capture-video');
            await CameraService.start(video);
            setState(STATE.PREVIEW);
        } catch (error) {
            setState(STATE.ERROR, error.message);
        }
    }

    /**
     * Close the modal and cleanup
     */
    function close() {
        if (isClosing) {
            return;
        }
        isClosing = true;

        // Stop camera first to prevent race condition
        CameraService.stop();

        // Clear any pending error timeout to prevent setState on closed modal
        if (errorTimeoutId) {
            clearTimeout(errorTimeoutId);
            errorTimeoutId = null;
        }

        // Remove keyboard listener to prevent memory leak
        if (keydownHandler) {
            document.removeEventListener('keydown', keydownHandler);
            keydownHandler = null;
        }

        // Remove beforeunload handler
        if (beforeUnloadHandler) {
            window.removeEventListener('beforeunload', beforeUnloadHandler);
            beforeUnloadHandler = null;
        }


        if (focusTrapHandler && modal) {
            modal.removeEventListener('keydown', focusTrapHandler);
            focusTrapHandler = null;
        }
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }

        capturedBlob = null;
        currentState = STATE.INITIALIZING;
        uploadRetryCount = 0; // Reset for next session
        isClosing = false;
    }

    /**
     * Capture the current frame
     */
    async function capturePhoto() {
        try {
            capturedBlob = await CameraService.capture(0.8);

            // Draw captured image to canvas for preview
            const canvas = document.getElementById('photo-capture-canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                canvas.width = 512;
                canvas.height = 512;
                ctx.drawImage(img, 0, 0, 512, 512);
                URL.revokeObjectURL(img.src);
                setState(STATE.CAPTURED);
            };

            img.onerror = () => {
                URL.revokeObjectURL(img.src);
                console.error('Failed to load captured image blob');
                setState(STATE.ERROR, 'Failed to load captured image. Please try again.');
            };

            img.src = URL.createObjectURL(capturedBlob);
        } catch (error) {
            setState(STATE.ERROR, 'Failed to capture photo. Please try again.');
        }
    }

    /**
     * Go back to preview mode for retake
     */
    function retakePhoto() {
        capturedBlob = null;
        setState(STATE.PREVIEW);
    }

    /**
     * Accept the captured photo
     */
    function usePhoto() {
        if (capturedBlob && onPhotoAccepted) {
            setState(STATE.UPLOADING);
            onPhotoAccepted(capturedBlob);
        }
    }

    /**
     * Show success and close
     */
    function showSuccess() {
        uploadRetryCount = 0; // Reset on success
        close();
    }

    /**
     * Show error in modal with retry limit
     */
    function showError(message) {
        uploadRetryCount++;

        // Check if max retries exceeded
        if (uploadRetryCount >= MAX_UPLOAD_RETRIES) {
            setState(STATE.ERROR, `${message} Maximum retries (${MAX_UPLOAD_RETRIES}) exceeded. Please close and try again later.`);
            // Don't auto-recover - user must close and reopen
            return;
        }

        const retriesLeft = MAX_UPLOAD_RETRIES - uploadRetryCount;
        setState(STATE.ERROR, `${message} (${retriesLeft} ${retriesLeft === 1 ? 'retry' : 'retries'} left)`);

        // Go back to captured state so user can retry (timeout is tracked and cleared on close)
        errorTimeoutId = setTimeout(() => {
            errorTimeoutId = null;
            if (capturedBlob) {
                setState(STATE.CAPTURED);
            } else {
                setState(STATE.PREVIEW);
            }
        }, 3000);
    }

    // Public API
    return {
        open,
        close,
        showSuccess,
        showError
    };
})();

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PhotoCaptureModal;
}
