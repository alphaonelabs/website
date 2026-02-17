/**
 * GitHub API Client
 */

const GITHUB_API_BASE = 'https://api.github.com';

/**
 * Make authenticated GitHub API request
 */
async function githubRequest(path, accessToken, options = {}) {
  const response = await fetch(`${GITHUB_API_BASE}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'OSS-Project-Management',
      ...options.headers
    }
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`GitHub API error: ${response.status} ${error}`);
  }

  return response.json();
}

/**
 * Fetch all issues from a repository
 */
export async function fetchRepositoryIssues(owner, repo, accessToken, state = 'all') {
  const issues = [];
  let page = 1;
  const perPage = 100;

  while (true) {
    const data = await githubRequest(
      `/repos/${owner}/${repo}/issues?state=${state}&per_page=${perPage}&page=${page}`,
      accessToken
    );

    if (data.length === 0) break;
    
    // Filter out pull requests
    const actualIssues = data.filter(item => !item.pull_request);
    issues.push(...actualIssues);

    if (data.length < perPage) break;
    page++;
  }

  return issues;
}

/**
 * Sync issues from GitHub to database
 */
export async function syncRepository(owner, repo, accessToken, env) {
  const repository = `${owner}/${repo}`;
  
  try {
    // Update sync status
    await env.DB.prepare(`
      INSERT INTO sync_status (repository, last_sync, status)
      VALUES (?, ?, 'in_progress')
      ON CONFLICT(repository) DO UPDATE SET
        last_sync = excluded.last_sync,
        status = 'in_progress',
        error_message = NULL
    `).bind(repository, new Date().toISOString()).run();

    // Fetch all issues
    const issues = await fetchRepositoryIssues(owner, repo, accessToken);

    // Store in database
    for (const issue of issues) {
      await syncIssue(issue, repository, env);
    }

    // Update sync status
    await env.DB.prepare(
      'UPDATE sync_status SET status = ?, last_sync = ? WHERE repository = ?'
    ).bind('completed', new Date().toISOString(), repository).run();

    // Update metrics
    await updateRepositoryMetrics(repository, env);

    return { success: true, count: issues.length };
  } catch (error) {
    // Update sync status with error
    await env.DB.prepare(
      'UPDATE sync_status SET status = ?, error_message = ? WHERE repository = ?'
    ).bind('failed', error.message, repository).run();

    throw error;
  }
}

/**
 * Sync single issue to database
 */
export async function syncIssue(issue, repository, env) {
  const timeToClose = issue.state === 'closed' && issue.closed_at
    ? calculateTimeToClose(issue.created_at, issue.closed_at)
    : null;

  // Insert or update issue
  await env.DB.prepare(`
    INSERT INTO issues (id, number, title, body, state, created_at, updated_at, closed_at, html_url, repository, assignee, milestone, time_to_close)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(repository, number) DO UPDATE SET
      title = excluded.title,
      body = excluded.body,
      state = excluded.state,
      updated_at = excluded.updated_at,
      closed_at = excluded.closed_at,
      assignee = excluded.assignee,
      milestone = excluded.milestone,
      time_to_close = excluded.time_to_close
  `).bind(
    issue.id,
    issue.number,
    issue.title,
    issue.body || '',
    issue.state,
    issue.created_at,
    issue.updated_at,
    issue.closed_at || null,
    issue.html_url,
    repository,
    issue.assignee?.login || null,
    issue.milestone?.title || null,
    timeToClose
  ).run();

  // Update labels
  await env.DB.prepare('DELETE FROM labels WHERE issue_id = ?').bind(issue.id).run();
  for (const label of issue.labels || []) {
    await env.DB.prepare(
      'INSERT INTO labels (issue_id, name, color) VALUES (?, ?, ?)'
    ).bind(issue.id, label.name, label.color).run();
  }

  // Update assignees
  await env.DB.prepare('DELETE FROM assignees WHERE issue_id = ?').bind(issue.id).run();
  for (const assignee of issue.assignees || []) {
    await env.DB.prepare(
      'INSERT INTO assignees (issue_id, username) VALUES (?, ?)'
    ).bind(issue.id, assignee.login).run();
  }
}

/**
 * Update issue on GitHub
 */
export async function updateGitHubIssue(owner, repo, issueNumber, updates, accessToken) {
  return githubRequest(
    `/repos/${owner}/${repo}/issues/${issueNumber}`,
    accessToken,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    }
  );
}

/**
 * Calculate time to close in hours
 */
export function calculateTimeToClose(createdAt, closedAt) {
  const created = new Date(createdAt);
  const closed = new Date(closedAt);
  return Math.round((closed - created) / (1000 * 60 * 60)); // hours
}

/**
 * Update repository metrics
 */
async function updateRepositoryMetrics(repository, env) {
  const today = new Date().toISOString().split('T')[0];

  const stats = await env.DB.prepare(`
    SELECT 
      COUNT(*) as total,
      SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) as open,
      SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) as closed,
      AVG(CASE WHEN time_to_close IS NOT NULL THEN time_to_close END) as avg_time
    FROM issues WHERE repository = ?
  `).bind(repository).first();

  await env.DB.prepare(`
    INSERT INTO metrics (repository, metric_date, total_issues, open_issues, closed_issues, avg_time_to_close)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(repository, metric_date) DO UPDATE SET
      total_issues = excluded.total_issues,
      open_issues = excluded.open_issues,
      closed_issues = excluded.closed_issues,
      avg_time_to_close = excluded.avg_time_to_close
  `).bind(
    repository,
    today,
    stats.total || 0,
    stats.open || 0,
    stats.closed || 0,
    stats.avg_time || 0
  ).run();
}
