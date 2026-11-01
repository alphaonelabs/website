"""
JavaScript application code
"""

JS_CONTENT = """let currentSort = 'updated_at';
let currentOrder = 'desc';
let currentPage = 1;
let selectedIssues = new Set();

// Check authentication
async function checkAuth() {
  try {
    const response = await fetch('/api/issues?repository=test/test&per_page=1');
    if (response.status === 401) {
      document.getElementById('auth-section').style.display = 'block';
    } else {
      document.getElementById('app-section').style.display = 'block';
    }
  } catch (error) {
    document.getElementById('auth-section').style.display = 'block';
  }
}

// Load issues
async function loadIssues(page = 1) {
  const repository = document.getElementById('repository').value;
  if (!repository) {
    showError('Please enter a repository (owner/repo)');
    return;
  }

  const state = document.getElementById('state').value;
  const label = document.getElementById('label').value;
  const assignee = document.getElementById('assignee').value;

  showLoading(true);
  hideError();

  try {
    const params = new URLSearchParams({
      repository,
      state,
      sort: currentSort,
      order: currentOrder,
      page,
      per_page: 50
    });

    if (label) params.append('label', label);
    if (assignee) params.append('assignee', assignee);

    const response = await fetch('/api/issues?' + params.toString());
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    displayIssues(data.issues);
    displayPagination(data.pagination);
    loadMetrics(repository);
    currentPage = page;

  } catch (error) {
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

// Display issues
function displayIssues(issues) {
  const tbody = document.getElementById('issues-body');
  tbody.innerHTML = '';

  if (issues.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 40px; color: #8b949e;">No issues found</td></tr>';
    document.getElementById('issues-table').style.display = 'table';
    return;
  }

  issues.forEach(issue => {
    const row = document.createElement('tr');
    
    const labels = issue.labels.map(l => 
      `<span class="label" style="background-color: #${l.color}; color: ${getContrastColor(l.color)}">${l.name}</span>`
    ).join('');

    const assignees = issue.assignees.map(a => 
      `<span class="assignee">@${a}</span>`
    ).join('');

    const createdDate = new Date(issue.created_at).toLocaleDateString();
    const timeToClose = issue.time_to_close 
      ? formatTimeToClose(issue.time_to_close)
      : '-';

    row.innerHTML = `
      <td><input type="checkbox" class="checkbox issue-checkbox" data-number="${issue.number}" onchange="updateSelection()" /></td>
      <td><a href="${issue.html_url}" target="_blank" class="issue-number">#${issue.number}</a></td>
      <td><span class="issue-title">${escapeHtml(issue.title)}</span></td>
      <td><span class="state-badge state-${issue.state}">${issue.state}</span></td>
      <td>${labels}</td>
      <td>${assignees}</td>
      <td class="time-value">${createdDate}</td>
      <td class="time-value">${timeToClose}</td>
    `;

    tbody.appendChild(row);
  });

  document.getElementById('issues-table').style.display = 'table';
}

// Load metrics
async function loadMetrics(repository) {
  try {
    const response = await fetch('/api/metrics?repository=' + encodeURIComponent(repository));
    const data = await response.json();

    if (!response.ok) return;

    const metricsHtml = `
      <div class="metric-card">
        <h3>Total Issues</h3>
        <div class="value">${data.current.total_issues || 0}</div>
      </div>
      <div class="metric-card">
        <h3>Open Issues</h3>
        <div class="value">${data.current.open_issues || 0}</div>
      </div>
      <div class="metric-card">
        <h3>Closed Issues</h3>
        <div class="value">${data.current.closed_issues || 0}</div>
      </div>
      <div class="metric-card">
        <h3>Avg Time to Close</h3>
        <div class="value">${data.current.avg_time_to_close_days || 0} days</div>
      </div>
    `;

    document.getElementById('metrics').innerHTML = metricsHtml;
  } catch (error) {
    console.error('Error loading metrics:', error);
  }
}

// Sort by column
function sortBy(field) {
  if (currentSort === field) {
    currentOrder = currentOrder === 'asc' ? 'desc' : 'asc';
  } else {
    currentSort = field;
    currentOrder = 'desc';
  }
  
  updateSortIndicators();
  loadIssues(currentPage);
}

// Update sort indicators
function updateSortIndicators() {
  document.querySelectorAll('th').forEach(th => {
    th.classList.remove('sorted-asc', 'sorted-desc');
  });
  const header = document.querySelector(`th[onclick*="${currentSort}"]`);
  if (header) {
    header.classList.add(currentOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');
  }
}

// Pagination
function displayPagination(pagination) {
  const div = document.getElementById('pagination');
  let html = '';

  if (pagination.page > 1) {
    html += `<button class="btn btn-secondary btn-small" onclick="loadIssues(${pagination.page - 1})">Previous</button>`;
  }

  html += `<span style="padding: 0 16px; color: #8b949e;">Page ${pagination.page} of ${pagination.total_pages}</span>`;

  if (pagination.page < pagination.total_pages) {
    html += `<button class="btn btn-secondary btn-small" onclick="loadIssues(${pagination.page + 1})">Next</button>`;
  }

  div.innerHTML = html;
}

// Selection management
function toggleSelectAll() {
  const selectAll = document.getElementById('select-all');
  const checkboxes = document.querySelectorAll('.issue-checkbox');
  checkboxes.forEach(cb => cb.checked = selectAll.checked);
  updateSelection();
}

function updateSelection() {
  selectedIssues.clear();
  document.querySelectorAll('.issue-checkbox:checked').forEach(cb => {
    selectedIssues.add(parseInt(cb.dataset.number));
  });

  const bulkActions = document.getElementById('bulk-actions');
  const selectedCount = document.getElementById('selected-count');
  
  if (selectedIssues.size > 0) {
    bulkActions.classList.add('active');
    selectedCount.textContent = `${selectedIssues.size} selected`;
  } else {
    bulkActions.classList.remove('active');
  }
}

function clearSelection() {
  selectedIssues.clear();
  document.querySelectorAll('.issue-checkbox').forEach(cb => cb.checked = false);
  document.getElementById('select-all').checked = false;
  updateSelection();
}

// Bulk operations
async function bulkClose() {
  await bulkUpdate({ state: 'closed' });
}

async function bulkReopen() {
  await bulkUpdate({ state: 'open' });
}

async function bulkUpdate(updates) {
  const repository = document.getElementById('repository').value;
  if (selectedIssues.size === 0) return;

  showLoading(true);
  try {
    const response = await fetch('/api/issues/bulk', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repository,
        issue_numbers: Array.from(selectedIssues),
        updates
      })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error);

    clearSelection();
    loadIssues(currentPage);
  } catch (error) {
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

// Sync repository
async function syncRepository() {
  const repository = document.getElementById('repository').value;
  if (!repository) {
    showError('Please enter a repository (owner/repo)');
    return;
  }

  showLoading(true);
  try {
    const response = await fetch('/api/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repository })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error);

    alert(`Synced ${data.count} issues from ${repository}`);
    loadIssues(currentPage);
  } catch (error) {
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

// Utility functions
function showLoading(show) {
  document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function showError(message) {
  const errorDiv = document.getElementById('error');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
}

function hideError() {
  document.getElementById('error').style.display = 'none';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function getContrastColor(hexColor) {
  const r = parseInt(hexColor.substr(0, 2), 16);
  const g = parseInt(hexColor.substr(2, 2), 16);
  const b = parseInt(hexColor.substr(4, 2), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 155 ? '#000' : '#fff';
}

function formatTimeToClose(hours) {
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w`;
}

// Initialize
checkAuth();
"""
