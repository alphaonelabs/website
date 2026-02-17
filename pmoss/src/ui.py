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
  <title>OSS Project Management</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header>
    <div class="container">
      <h1>🚀 OSS Project Management</h1>
    </div>
  </header>

  <div class="container">
    <div id="auth-section" class="auth-section" style="display: none;">
      <h2>Welcome to OSS Project Management</h2>
      <p>Connect with GitHub to manage your issues and track project metrics</p>
      <a href="/auth" class="btn">Connect with GitHub</a>
    </div>

    <div id="app-section" style="display: none;">
      <div id="metrics" class="metrics"></div>

      <div class="controls">
        <div class="control-row">
          <div class="control-group">
            <label>Repository:</label>
            <input type="text" id="repository" placeholder="owner/repo" />
          </div>
          <button class="btn btn-secondary btn-small" onclick="syncRepository()">Sync</button>
          <button class="btn btn-small" onclick="loadIssues()">Load Issues</button>
        </div>
        
        <div class="control-row">
          <div class="control-group">
            <label>State:</label>
            <select id="state">
              <option value="all">All</option>
              <option value="open" selected>Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          <div class="control-group">
            <label>Label:</label>
            <input type="text" id="label" placeholder="bug, feature, etc." />
          </div>

          <div class="control-group">
            <label>Assignee:</label>
            <input type="text" id="assignee" placeholder="username" />
          </div>
        </div>
      </div>

      <div id="bulk-actions" class="bulk-actions">
        <span id="selected-count">0 selected</span>
        <button class="btn btn-small" onclick="bulkClose()">Close Selected</button>
        <button class="btn btn-small" onclick="bulkReopen()">Reopen Selected</button>
        <button class="btn btn-secondary btn-small" onclick="clearSelection()">Clear</button>
      </div>

      <div id="error" class="error" style="display: none;"></div>
      <div id="loading" class="loading" style="display: none;">Loading...</div>
      
      <table id="issues-table" style="display: none;">
        <thead>
          <tr>
            <th><input type="checkbox" class="checkbox" id="select-all" onchange="toggleSelectAll()" /></th>
            <th class="sortable" onclick="sortBy('number')">#</th>
            <th class="sortable" onclick="sortBy('title')">Title</th>
            <th class="sortable" onclick="sortBy('state')">State</th>
            <th>Labels</th>
            <th>Assignees</th>
            <th class="sortable" onclick="sortBy('created_at')">Created</th>
            <th class="sortable" onclick="sortBy('time_to_close')">Time to Close</th>
          </tr>
        </thead>
        <tbody id="issues-body"></tbody>
      </table>

      <div id="pagination" class="pagination"></div>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>"""


def serve_ui(env):
    """Serve the frontend HTML application"""
    headers = Headers.new()
    headers.set('Content-Type', 'text/html')
    return Response.new(HTML_TEMPLATE, headers=headers)
