// Helper to get the CSRF token from cookies:
function getCSRFToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let c of cookies) {
    c = c.trim();
    if (c.startsWith(name + '=')) {
      return decodeURIComponent(c.substring(name.length + 1));
    }
  }
  return '';
}

// A simple wrapper for POSTing JSON with CSRF:
function ajaxPost(url, data, onSuccess, onError) {
  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
    },
    body: JSON.stringify(data),
  })
    .then((resp) => {
      if (!resp.ok) throw new Error('Network response was not OK');
      return resp.json();
    })
    .then(onSuccess)
    .catch(onError);
}

// A simple wrapper for GETting JSON:
function ajaxGet(url, onSuccess, onError) {
  fetch(url)
    .then((resp) => {
      if (!resp.ok) throw new Error('Network response was not OK');
      return resp.json();
    })
    .then(onSuccess)
    .catch(onError);
}
