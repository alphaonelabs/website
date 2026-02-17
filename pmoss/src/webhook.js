/**
 * GitHub Webhook Handler
 */

import { syncIssue, calculateTimeToClose } from './github';

/**
 * Verify webhook signature
 */
async function verifyWebhookSignature(request, env) {
  const signature = request.headers.get('X-Hub-Signature-256');
  if (!signature) {
    return false;
  }

  const body = await request.text();
  const secret = env.GITHUB_WEBHOOK_SECRET;
  
  if (!secret) {
    console.warn('GITHUB_WEBHOOK_SECRET not configured');
    return true; // Allow in development
  }

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signed = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const expectedSignature = 'sha256=' + Array.from(new Uint8Array(signed))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  return signature === expectedSignature;
}

/**
 * Handle GitHub webhook
 */
export async function handleWebhook(request, env) {
  // Verify signature
  const isValid = await verifyWebhookSignature(request.clone(), env);
  if (!isValid) {
    return new Response('Invalid signature', { status: 401 });
  }

  const event = request.headers.get('X-GitHub-Event');
  const payload = await request.json();

  try {
    if (event === 'issues') {
      await handleIssueEvent(payload, env);
    } else if (event === 'ping') {
      return new Response(JSON.stringify({ message: 'Webhook configured successfully' }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({ status: 'processed' }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Webhook processing error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Handle issue events
 */
async function handleIssueEvent(payload, env) {
  const issue = payload.issue;
  const action = payload.action;
  const repository = payload.repository.full_name;

  console.log(`Processing issue event: ${action} for ${repository}#${issue.number}`);

  // Calculate time to close
  let timeToClose = null;
  if (issue.state === 'closed' && issue.closed_at) {
    timeToClose = calculateTimeToClose(issue.created_at, issue.closed_at);
  }

  // Upsert issue
  const result = await env.DB.prepare(`
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

  // Update metrics
  await updateMetrics(repository, env);
}

/**
 * Update repository metrics
 */
async function updateMetrics(repository, env) {
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
