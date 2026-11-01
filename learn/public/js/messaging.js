//Privacy-First Messaging Client logic
(function () {
  'use strict';

  let activeThreadId = null;

  function getAuthToken() {
    return localStorage.getItem('edu_token') || localStorage.getItem('token') || localStorage.getItem('authToken') || '';
  }

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }

  async function loadPendingRequests() {
    const listEl = document.getElementById('pending-requests-list');
    if (!listEl) return;

    const token = getAuthToken();
    if (!token) {
      listEl.innerHTML = '<div class="text-xs text-gray-500 italic">Sign in to view pending requests.</div>';
      return;
    }

    try {
      const res = await fetch('/api/messages/requests', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load requests');

      const requests = (data.data && data.data.requests) || data.requests || [];
      if (!requests.length) {
        listEl.innerHTML = '<div class="text-xs text-gray-500 dark:text-gray-400 italic">No pending message requests.</div>';
        return;
      }

      listEl.innerHTML = requests.map(function (req) {
        const date = req.created_at ? req.created_at.slice(0, 10) : '';
        const senderName = req.from_user_name || (req.source === 'activity' ? 'Activity Participant' : 'Email Sender');
        return (
          '<div class="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900" data-req-id="' + esc(req.id) + '">' +
            '<div>' +
              '<div class="text-xs font-bold text-teal-600 dark:text-teal-300">' + esc(senderName) + '</div>' +
              '<div class="text-[10px] text-gray-500 dark:text-gray-400">' + esc(date) + '</div>' +
            '</div>' +
            '<div class="flex items-center space-x-2">' +
              '<button type="button" data-action="accept" class="px-2.5 py-1 text-xs font-semibold rounded bg-teal-600 hover:bg-teal-700 text-white transition-colors">Accept</button>' +
              '<button type="button" data-action="decline" class="px-2.5 py-1 text-xs font-semibold rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 transition-colors">Decline</button>' +
            '</div>' +
          '</div>'
        );
      }).join('');

      listEl.querySelectorAll('button[data-action]').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          const reqItem = btn.closest('[data-req-id]');
          if (!reqItem) return;
          const reqId = reqItem.getAttribute('data-req-id');
          const action = btn.getAttribute('data-action');
          await respondToRequest(reqId, action, reqItem);
        });
      });
    } catch (err) {
      listEl.innerHTML = '<div class="text-xs text-red-500">' + esc(err.message) + '</div>';
    }
  }

  async function respondToRequest(reqId, action, reqItem) {
    const token = getAuthToken();
    if (!token) return;

    try {
      const res = await fetch('/api/messages/request/' + encodeURIComponent(reqId), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ action: action })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to update request');

      if (reqItem) {
        reqItem.remove();
      }
      loadPendingRequests();
      loadActiveThreads();
    } catch (err) {
      alert(err.message);
    }
  }

  async function loadActiveThreads() {
    const listEl = document.getElementById('active-threads-list');
    if (!listEl) return;

    const token = getAuthToken();
    if (!token) {
      listEl.innerHTML = '<div class="text-xs text-gray-500 italic">Sign in to view conversations.</div>';
      return;
    }

    try {
      const res = await fetch('/api/messages/threads', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load conversations');

      const threads = (data.data && data.data.threads) || data.threads || [];
      if (!threads.length) {
        listEl.innerHTML = '<div class="text-xs text-gray-500 dark:text-gray-400 italic">No active conversations yet. Accept a request to start chatting!</div>';
        return;
      }

      listEl.innerHTML = threads.map(function (t) {
        const unreadDot = t.has_unread ? '<span class="w-2.5 h-2.5 rounded-full bg-red-500 inline-block mr-1.5 animate-pulse" title="New unread message"></span>' : '';
        return (
          '<div class="flex items-center justify-between p-3.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 shadow-sm">' +
            '<div class="flex items-center space-x-3">' +
              '<div class="w-9 h-9 rounded-full bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 flex items-center justify-center font-bold text-sm shrink-0">' +
                esc(String(t.other_user_name || 'C').slice(0, 1).toUpperCase()) +
              '</div>' +
              '<div>' +
                '<div class="text-sm font-bold text-gray-900 dark:text-gray-100">' + esc(t.other_user_name) + '</div>' +
                '<div class="text-[10px] text-gray-500 dark:text-gray-400">Connected</div>' +
              '</div>' +
            '</div>' +
            '<button type="button" data-thread-id="' + esc(t.id) + '" data-name="' + esc(t.other_user_name) + '" class="open-chat-btn inline-flex items-center px-4 py-1.5 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-700 text-white transition-colors shadow-sm">' +
              unreadDot + '<i class="fa-solid fa-comments mr-1.5"></i>Chat' +
            '</button>' +
          '</div>'
        );
      }).join('');

      listEl.querySelectorAll('.open-chat-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          const threadId = btn.getAttribute('data-thread-id');
          const name = btn.getAttribute('data-name');
          openChat(threadId, name);
        });
      });
    } catch (err) {
      listEl.innerHTML = '<div class="text-xs text-red-500">' + esc(err.message) + '</div>';
    }
  }

  async function openChat(threadId, otherUserName) {
    activeThreadId = threadId;
    const modal = document.getElementById('chat-modal');
    const titleEl = document.getElementById('chat-title');
    const historyEl = document.getElementById('chat-history');

    if (!modal || !historyEl) return;

    if (titleEl) titleEl.textContent = 'Chat with ' + (otherUserName || 'Connected User');
    historyEl.innerHTML = '<div class="text-xs text-gray-500 italic text-center py-4">Loading messages...</div>';
    modal.classList.remove('hidden');

    await refreshChatHistory();
  }

  async function refreshChatHistory() {
    if (!activeThreadId) return;
    const historyEl = document.getElementById('chat-history');
    const token = getAuthToken();
    if (!historyEl || !token) return;

    try {
      const res = await fetch('/api/messages/threads/' + encodeURIComponent(activeThreadId), {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load chat');

      const threadObj = (data.data && data.data.thread) || data.thread || {};
      const currentUserId = threadObj.current_user_id || '';
      const otherUserName = threadObj.other_user_name || 'Connected User';
      const msgs = (data.data && data.data.messages) || data.messages || [];

      if (!msgs.length) {
        historyEl.innerHTML = '<div class="text-xs text-gray-500 dark:text-gray-400 italic text-center py-6">No messages yet. Send a message to start the conversation!</div>';
        return;
      }

      historyEl.innerHTML = msgs.map(function (m) {
        const time = m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        const isMe = currentUserId && m.sender === currentUserId;
        const senderName = isMe ? 'You' : otherUserName;
        const flexCls = isMe ? 'flex justify-end' : 'flex justify-start';
        const bubbleCls = isMe
          ? 'bg-teal-600 text-white rounded-2xl rounded-tr-none p-3 max-w-[80%]'
          : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-2xl rounded-tl-none p-3 max-w-[80%]';
        const metaCls = isMe ? 'text-teal-100' : 'text-gray-500 dark:text-gray-400';

        return (
          '<div class="' + flexCls + ' mb-2">' +
            '<div class="' + bubbleCls + '">' +
              '<div class="flex items-center justify-between gap-3 text-[10px] ' + metaCls + ' font-bold mb-1">' +
                '<span>' + esc(senderName) + '</span>' +
                '<span>' + esc(time) + '</span>' +
              '</div>' +
              '<div class="whitespace-pre-wrap text-xs font-medium">' + esc(m.content) + '</div>' +
            '</div>' +
          '</div>'
        );
      }).join('');
      historyEl.scrollTop = historyEl.scrollHeight;
    } catch (err) {
      historyEl.innerHTML = '<div class="text-xs text-red-500 text-center py-4">' + esc(err.message) + '</div>';
    }
  }

  function initChatModal() {
    const closeBtn = document.getElementById('close-chat-btn');
    const modal = document.getElementById('chat-modal');
    const form = document.getElementById('chat-send-form');
    const input = document.getElementById('chat-input');

    function closeModal() {
      if (modal) modal.classList.add('hidden');
      activeThreadId = null;
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', closeModal);
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
        closeModal();
      }
    });

    if (form && input) {
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const text = (input.value || '').trim();
        if (!text || !activeThreadId) return;

        const token = getAuthToken();
        if (!token) return;

        try {
          const res = await fetch('/api/messages/threads/' + encodeURIComponent(activeThreadId) + '/send', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({ message: text })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || 'Could not send message');

          input.value = '';
          await refreshChatHistory();
        } catch (err) {
          alert(err.message);
        }
      });
    }
  }

  function initForm() {
    const form = document.getElementById('send-request-form');
    if (!form) return;

    const emailInput = document.getElementById('request-email');
    const feedbackEl = document.getElementById('request-feedback');

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      const email = (emailInput.value || '').trim();
      if (!email) return;

      const token = getAuthToken();
      if (!token) {
        if (feedbackEl) {
          feedbackEl.className = 'mt-3 text-xs p-3 rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
          feedbackEl.textContent = 'Please sign in to send message requests.';
          feedbackEl.classList.remove('hidden');
        }
        return;
      }

      try {
        const res = await fetch('/api/messages/request', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ email: email })
        });
        const data = await res.json();

        if (feedbackEl) {
          if (!res.ok) {
            feedbackEl.className = 'mt-3 text-xs p-3 rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
            feedbackEl.textContent = data.error || 'Failed to send request.';
          } else {
            feedbackEl.className = 'mt-3 text-xs p-3 rounded-lg bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-200';
            feedbackEl.textContent = data.message || "We'll let the other person know you'd like to message them and they can accept to reply.";
            emailInput.value = '';
          }
          feedbackEl.classList.remove('hidden');
        }
      } catch (err) {
        if (feedbackEl) {
          feedbackEl.className = 'mt-3 text-xs p-3 rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
          feedbackEl.textContent = err.message || 'Network error.';
          feedbackEl.classList.remove('hidden');
        }
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initForm();
    loadPendingRequests();
    loadActiveThreads();
    initChatModal();

    // Auto-update chat history, threads, and requests every 4 seconds when tab is active
    setInterval(function () {
      if (document.hidden) return;
      loadActiveThreads();
      loadPendingRequests();
      if (activeThreadId) {
        refreshChatHistory();
      }
    }, 4000);
  });
})();

