// Forum authoring: start topics, reply, and delete your own posts.
// Pages are server-rendered; this script only wires up the forms and buttons.
// The API enforces every rule shown here (sign-in, verified email, ownership).
(function () {
  'use strict';

  function readToken() {
    try { return localStorage.getItem('edu_token') || ''; } catch (e) { return ''; }
  }

  function readUser() {
    try { return JSON.parse(localStorage.getItem('edu_user') || 'null'); } catch (e) { return null; }
  }

  const token = readToken();
  const user = readUser();
  const signedIn = Boolean(token && user);

  function show(el) { if (el) el.classList.remove('hidden'); }
  function hide(el) { if (el) el.classList.add('hidden'); }

  function setStatus(el, message, isError) {
    if (!el) return;
    el.className = 'rounded-lg p-3 text-sm ' + (isError
      ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
      : 'bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300');
    el.textContent = message;
  }

  function errorMessage(status, data) {
    if (status === 401) return 'Your session has expired. Please sign in again.';
    if (status === 429) return 'You are posting too quickly. Please wait a few minutes and try again.';
    return (data && data.error) || 'Something went wrong. Please try again.';
  }

  async function send(method, url, payload) {
    const headers = { Authorization: 'Bearer ' + token };
    const options = { method: method, headers: headers };
    if (payload !== undefined) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(payload);
    }
    const res = await fetch(url, options);
    let data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) throw new Error(errorMessage(res.status, data));
    return data;
  }

  function setBusy(form, busy) {
    form.querySelectorAll('button, input, textarea').forEach(function (el) { el.disabled = busy; });
  }

  // ── /forum: new topic form ──────────────────────────────────────────
  const topicForm = document.getElementById('forum-topic-form');
  if (topicForm) {
    const toggle = document.getElementById('forum-compose-toggle');
    const signin = document.getElementById('forum-compose-signin');
    const cancel = document.getElementById('forum-topic-cancel');
    const status = document.getElementById('forum-topic-status');
    const titleInput = document.getElementById('forum-topic-title');

    if (signedIn) {
      hide(signin);
      show(toggle);
    }

    function setOpen(open) {
      if (open) { show(topicForm); hide(toggle); } else { hide(topicForm); show(toggle); }
      if (toggle) toggle.setAttribute('aria-expanded', String(open));
      if (open && titleInput) titleInput.focus();
    }

    if (toggle) toggle.addEventListener('click', function () { setOpen(true); });
    if (cancel) cancel.addEventListener('click', function () { setOpen(false); hide(status); });

    topicForm.addEventListener('submit', async function (event) {
      event.preventDefault();
      if (!topicForm.reportValidity()) return;
      setBusy(topicForm, true);
      setStatus(status, 'Posting…', false);
      show(status);
      try {
        const data = await send('POST', '/api/forum/topics', {
          title: topicForm.elements.title.value,
          body: topicForm.elements.body.value,
        });
        window.location.href = (data.data && data.data.url) || '/forum';
      } catch (err) {
        setStatus(status, err.message, true);
        setBusy(topicForm, false);
      }
    });
  }

  // ── /forum/topic/<id>: reply form ───────────────────────────────────
  const replyForm = document.getElementById('forum-reply-form');
  if (replyForm) {
    const signinNote = document.getElementById('forum-reply-signin');
    const status = document.getElementById('forum-reply-status');
    if (signedIn) {
      show(replyForm);
      hide(signinNote);
    }

    replyForm.addEventListener('submit', async function (event) {
      event.preventDefault();
      if (!replyForm.reportValidity()) return;
      const topicId = replyForm.dataset.topicId;
      setBusy(replyForm, true);
      setStatus(status, 'Posting…', false);
      show(status);
      try {
        const data = await send('POST', '/api/forum/topics/' + encodeURIComponent(topicId) + '/replies', {
          body: replyForm.elements.body.value,
        });
        const replyId = (data.data && data.data.id) || '';
        // A fresh query string avoids showing a cached copy of the thread.
        window.location.href = window.location.pathname + '?posted=' + Date.now() + (replyId ? '#reply-' + replyId : '');
      } catch (err) {
        setStatus(status, err.message, true);
        setBusy(replyForm, false);
      }
    });
  }

  // ── Delete buttons (shown to the author and to admins) ──────────────
  if (signedIn) {
    document.querySelectorAll('[data-forum-delete]').forEach(function (btn) {
      const isAuthor = user.id && btn.dataset.forumAuthor === String(user.id);
      if (!isAuthor && user.role !== 'admin') return;
      show(btn);
      btn.addEventListener('click', async function () {
        const kind = btn.dataset.forumDelete;
        const id = btn.dataset.forumId;
        const prompt = kind === 'topic'
          ? 'Delete this topic and all of its replies? This cannot be undone.'
          : 'Delete this reply? This cannot be undone.';
        if (!window.confirm(prompt)) return;
        btn.disabled = true;
        try {
          const path = kind === 'topic' ? '/api/forum/topics/' : '/api/forum/replies/';
          await send('DELETE', path + encodeURIComponent(id));
          if (kind === 'topic') {
            window.location.href = '/forum?deleted=' + Date.now();
          } else {
            const article = btn.closest('article');
            if (article) article.remove();
          }
        } catch (err) {
          btn.disabled = false;
          window.alert(err.message);
        }
      });
    });
  }
})();
