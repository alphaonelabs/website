/**
 * Helper function to get CSRF token from cookies
 */
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

/**
 * Custom preview renderer for EasyMDE that uses the sanitized server-side endpoint.
 * @param {string} plainText The raw markdown text from the editor.
 * @param {string} previewUrl The URL of the markdownify endpoint.
 * @returns {string} The sanitized HTML from the server.
 */
function sanitizedPreviewRender(plainText, previewUrl) {
    const formData = new FormData();
    formData.append('content', plainText);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', previewUrl, false); // Synchronous request as required by EasyMDE
    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
    xhr.send(formData);

    if (xhr.status === 200) {
        return xhr.responseText;
    }

    return '<p style="color: red;">Error rendering markdown preview.</p>';
}
