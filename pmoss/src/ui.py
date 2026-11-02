"""
UI Handler - Serve the frontend application
"""

from js import Response, Headers


# HTML template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PMOSS — OSS Project Management</title>
  <link rel="stylesheet" href="https://design.alphaonelabs.com/brand.css">
  <link rel="stylesheet" href="/static/styles.css">
  <script src="https://design.alphaonelabs.com/chrome.js" defer></script>
</head>
<body>
  <a1-header site="PMOSS" site-href="/" sticky compact></a1-header>

  <main class="container">
    <div class="page-intro">
      <div>
        <p class="eyebrow">Alpha One Labs / Open Source</p>
        <h1>OSS Project Management</h1>
        <hr class="a1-rule">
        <p class="lead">Manage GitHub issues and track project health in one place.</p>
      </div>
      <div class="pcb-art" aria-hidden="true"></div>
    </div>
    <hr class="a1-trace">

    <div id="auth-section" class="auth-section" style="display: none;">
      <h2>Welcome to OSS Project Management</h2>
      <p>Connect with GitHub to manage your issues and track project metrics</p>
      <a href="/auth" class="btn">Connect with GitHub</a>
    </div>

    <div id="app-section" style="display: none;">
      <div id="metrics" class="metrics" aria-live="polite"></div>

      <div class="controls">
        <div class="control-row">
          <div class="control-group">
            <label for="repository">Repository:</label>
            <input type="text" id="repository" placeholder="owner/repo" />
          </div>
          <button class="btn btn-secondary btn-small" onclick="syncRepository()">Sync</button>
          <button class="btn btn-small" onclick="loadIssues()">Load Issues</button>
        </div>

        <div class="control-row">
          <div class="control-group">
            <label for="state">State:</label>
            <select id="state">
              <option value="all">All</option>
              <option value="open" selected>Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          <div class="control-group">
            <label for="label">Label:</label>
            <input type="text" id="label" placeholder="bug, feature, etc." />
          </div>

          <div class="control-group">
            <label for="assignee">Assignee:</label>
            <input type="text" id="assignee" placeholder="username" />
          </div>
        </div>
      </div>

      <div id="bulk-actions" class="bulk-actions" role="region" aria-label="Bulk actions">
        <span id="selected-count" aria-live="polite">0 selected</span>
        <button class="btn btn-secondary btn-small" onclick="bulkClose()">Close Selected</button>
        <button class="btn btn-secondary btn-small" onclick="bulkReopen()">Reopen Selected</button>
        <button class="btn btn-secondary btn-small" onclick="clearSelection()">Clear</button>
      </div>

      <div id="error" class="error" role="alert" style="display: none;"></div>
      <div id="loading" class="loading" role="status" style="display: none;">Loading...</div>

      <div class="table-wrap">
      <table id="issues-table" style="display: none;">
        <caption class="sr-only">Repository issues</caption>
        <thead>
          <tr>
            <th scope="col"><input type="checkbox" class="checkbox" id="select-all" aria-label="Select all issues" onchange="toggleSelectAll()" /></th>
            <th scope="col" class="sortable" onclick="sortBy('number')">#</th>
            <th scope="col" class="sortable" onclick="sortBy('title')">Title</th>
            <th scope="col" class="sortable" onclick="sortBy('state')">State</th>
            <th scope="col">Labels</th>
            <th scope="col">Assignees</th>
            <th scope="col" class="sortable" onclick="sortBy('created_at')">Created</th>
            <th scope="col" class="sortable" onclick="sortBy('time_to_close')">Time to Close</th>
          </tr>
        </thead>
        <tbody id="issues-body"></tbody>
      </table>
      </div>

      <div id="pagination" class="pagination"></div>
    </div>
  </main>

  <a1-footer source="pmoss"></a1-footer>

  <script src="/static/app.js"></script>
</body>
</html>"""


def serve_ui(env):
    """Serve the frontend HTML application"""
    headers = Headers.new()
    headers.set('Content-Type', 'text/html')
    return Response.new(HTML_TEMPLATE, headers=headers)
