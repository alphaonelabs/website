(function () {
  const root = document.querySelector('[data-records-page]');
  if (!root) return;
  if (root.dataset.serverRendered === 'true') return;

  const group = root.dataset.group || 'community';
  const models = root.dataset.models || '';
  const title = root.dataset.title || 'Records';
  const noun = root.dataset.noun || 'record';
  const authRequired = root.dataset.authRequired !== 'false';

  function esc(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function modelLabel(model) {
    return String(model || '')
      .replace(/^web\./, '')
      .replace(/([a-z])([A-Z])/g, '$1 $2');
  }

  function iconFor(model) {
    const m = String(model || '').toLowerCase();
    if (m.includes('forum')) return 'fa-comments';
    if (m.includes('blog')) return 'fa-blog';
    if (m.includes('study')) return 'fa-users';
    if (m.includes('quiz')) return 'fa-circle-question';
    if (m.includes('survey') || m.includes('question')) return 'fa-square-poll-vertical';
    if (m.includes('challenge')) return 'fa-trophy';
    if (m.includes('progress') || m.includes('streak') || m.includes('points')) return 'fa-chart-line';
    if (m.includes('grade') || m.includes('link')) return 'fa-link';
    if (m.includes('calendar') || m.includes('slot')) return 'fa-calendar-days';
    if (m.includes('meme')) return 'fa-face-smile';
    if (m.includes('success')) return 'fa-star';
    if (m.includes('message')) return 'fa-envelope';
    if (m.includes('feature')) return 'fa-lightbulb';
    return 'fa-layer-group';
  }

  function setStatus(message, isError) {
    const status = document.getElementById('records-status');
    if (!status) return;
    status.className = 'rounded-lg p-4 text-sm ' + (isError
      ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
      : 'bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300');
    status.textContent = message;
    status.classList.remove('hidden');
  }

  function render(records) {
    const holder = document.getElementById('records-list');
    const count = document.getElementById('records-count');
    if (count) count.textContent = String(records.length);
    if (!records.length) {
      holder.innerHTML = '<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">No ' + esc(noun) + ' found yet.</div>';
      return;
    }
    holder.innerHTML = records.map((record) => {
      const date = record.created_at ? String(record.created_at).slice(0, 10) : '';
      const label = modelLabel(record.model);
      const icon = iconFor(record.model);
      const routeUrl = record.route_url || '';
      const imageUrl = record.image_url || '';
      const titleHtml = routeUrl
        ? '<a href="' + esc(routeUrl) + '" class="hover:text-teal-700 dark:hover:text-teal-300">' + esc(record.title) + '</a>'
        : esc(record.title);
      const imageHtml = imageUrl
        ? '<a href="' + esc(routeUrl || record.url || '#') + '" class="block sm:w-44 shrink-0 rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-900 border border-gray-100 dark:border-gray-700"><img src="' + esc(imageUrl) + '" alt="' + esc(record.title) + '" class="w-full aspect-video sm:aspect-square object-cover" loading="lazy" onerror="this.closest(\'a\').remove();"></a>'
        : '<div class="hidden sm:flex w-11 h-11 rounded-full bg-teal-100 dark:bg-teal-900 items-center justify-center text-teal-600 dark:text-teal-300 shrink-0"><i class="fa-solid ' + icon + '"></i></div>';
      return '<article class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">' +
        '<div class="flex flex-col sm:flex-row items-start gap-4">' +
          imageHtml +
          '<div class="min-w-0 flex-1">' +
            '<div class="flex flex-wrap items-center justify-between gap-2 mb-1 text-xs text-gray-500 dark:text-gray-400">' +
              '<span class="font-medium text-teal-600 dark:text-teal-300">' + esc(label) + '</span>' +
              (date ? '<span>' + esc(date) + '</span>' : '') +
            '</div>' +
            '<h2 class="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">' + titleHtml + '</h2>' +
            (record.description ? '<p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">' + esc(record.description) + '</p>' : '') +
            '<div class="mt-3 flex flex-wrap gap-2 text-xs">' +
              (record.status ? '<span class="rounded-full bg-gray-100 dark:bg-gray-900 px-3 py-1 text-gray-600 dark:text-gray-300">' + esc(record.status) + '</span>' : '') +
              (record.amount ? '<span class="rounded-full bg-amber-100 dark:bg-amber-900/30 px-3 py-1 text-amber-700 dark:text-amber-300">' + esc(record.amount) + '</span>' : '') +
              (record.url ? '<a href="' + esc(record.url) + '" target="_blank" rel="noopener" class="rounded-full bg-teal-100 dark:bg-teal-900/30 px-3 py-1 text-teal-700 dark:text-teal-300 hover:underline">Open link</a>' : '') +
              (routeUrl ? '<a href="' + esc(routeUrl) + '" class="rounded-full bg-cyan-100 dark:bg-cyan-900/30 px-3 py-1 text-cyan-700 dark:text-cyan-300 hover:underline">Open page</a>' : '') +
            '</div>' +
          '</div>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  async function load() {
    const token = localStorage.getItem('edu_token');
    if (authRequired && !token) {
      setStatus('Sign in to view ' + title.toLowerCase() + '.', true);
      document.getElementById('records-list').innerHTML = '<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center"><p class="text-gray-600 dark:text-gray-300 mb-4">This section uses your Alpha One Labs account.</p><a href="/login" class="inline-flex items-center px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold"><i class="fa-solid fa-right-to-bracket mr-2"></i>Sign in</a></div>';
      return;
    }

    try {
      const params = new URLSearchParams({ group });
      if (models) params.set('models', models);
      const headers = token ? { Authorization: 'Bearer ' + token } : {};
      const res = await fetch('/api/features?' + params.toString(), { headers });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || 'Could not load ' + title.toLowerCase());
      render(body.records || []);
    } catch (err) {
      setStatus(err.message, true);
    }
  }

  load();
})();
