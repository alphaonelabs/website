/**
 * Camera Service for capturing photos
 * Provides a clean API for camera access, capture, and resource management
 */
const CameraService = (function() {
    'use strict';

    let stream = null;
    let videoElement = null;

    /**
     * Check if camera capture is supported
     * @returns {boolean} True if camera is supported
     */
    function isSupported() {
        // Check for secure context (HTTPS or localhost)
        const isSecureContext = window.isSecureContext ||
            window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1';

        // Check for getUserMedia support
        const hasGetUserMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);

        return isSecureContext && hasGetUserMedia;
    }

    /**
     * Start the camera and attach to video element
     * @param {HTMLVideoElement} video - The video element to attach the stream to
     * @returns {Promise<MediaStream>} The media stream
     */
    async function start(video) {
        if (!isSupported()) {
            throw new Error('Camera not supported in this context');
        }

        // Stop and release any existing stream to prevent leaks
        stop();

        try {
            // Request camera with constraints optimized for avatar capture
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 512, max: 1280 },
                    height: { ideal: 512, max: 1280 },
                    facingMode: 'user'  // Front camera for selfies
                },
                audio: false
            });

            videoElement = video;
            video.srcObject = stream;

            // Wait for video to be ready with timeout to prevent indefinite hang
            await new Promise((resolve, reject) => {
                const TIMEOUT_MS = 10000; // 10 seconds timeout
                let timeoutId = null;

                const cleanup = () => {
                    if (timeoutId) {
                        clearTimeout(timeoutId);
                        timeoutId = null;
                    }
                    video.onloadedmetadata = null;
                    video.onerror = null;
                };

                timeoutId = setTimeout(() => {
                    cleanup();
                    reject(new Error('Camera initialization timeout. Please try again.'));
                }, TIMEOUT_MS);

                video.onloadedmetadata = () => {
                    cleanup();
                    video.play()
                        .then(resolve)
                        .catch(reject);
                };

                video.onerror = (err) => {
                    cleanup();
                    reject(err);
                };
            });

            return stream;
        } catch (error) {
            stop();

            // Provide user-friendly error messages
            if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                throw new Error('Camera permission denied. Please allow camera access and try again.');
            } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                throw new Error('No camera found. Please connect a camera and try again.');
            } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
                throw new Error('Camera is already in use by another application.');
            } else if (error.name === 'OverconstrainedError') {
                throw new Error('Camera does not meet the required constraints.');
            } else if (error.name === 'SecurityError') {
                throw new Error('Camera access requires a secure connection (HTTPS).');
            }

            throw error;
        }
    }

    /**
     * Capture the current frame as a JPEG blob
     * @param {number} quality - JPEG quality (0-1), default 0.8
     * @returns {Promise<Blob>} The captured image as a Blob
     */
    async function capture(quality = 0.8) {
        if (!videoElement || !stream) {
            throw new Error('Camera not started');
        }

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        // Get video dimensions
        const videoWidth = videoElement.videoWidth;
        const videoHeight = videoElement.videoHeight;

        // Calculate square crop (center crop for avatar)
        const size = Math.min(videoWidth, videoHeight);
        const offsetX = (videoWidth - size) / 2;
        const offsetY = (videoHeight - size) / 2;

        // Set canvas to 512x512 for avatar
        const outputSize = 512;
        canvas.width = outputSize;
        canvas.height = outputSize;

        // Draw cropped and scaled image
        ctx.drawImage(
            videoElement,
            offsetX, offsetY, size, size,  // Source (center crop)
            0, 0, outputSize, outputSize   // Destination (512x512)
        );

        // Convert to blob and cleanup canvas
        return new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => {
                    // Clear canvas to release memory
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    canvas.width = 0;
                    canvas.height = 0;

                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error('Failed to capture image'));
                    }
                },
                'image/jpeg',
                quality
            );
        });
    }

    /**
     * Stop the camera and release all resources
     */
    function stop() {
        if (stream) {
            stream.getTracks().forEach(track => {
                track.stop();
            });
            stream = null;
        }

        if (videoElement) {
            videoElement.srcObject = null;
            videoElement = null;
        }
    }

    /**
     * Check if camera is currently active
     * @returns {boolean} True if camera is active
     */
    function isActive() {
        return stream !== null && stream.active;
    }

    // Public API
    return {
        isSupported,
        start,
        capture,
        stop,
        isActive
    };
})();

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CameraService;
}
