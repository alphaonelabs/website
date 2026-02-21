"""
GitHub Webhook Handler
"""

from js import Response, Headers, crypto
import json
from github import sync_issue, calculate_time_to_close, update_repository_metrics


async def verify_webhook_signature(request, env):
    """Verify webhook signature"""
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        return False
    
    body = await request.text()
    secret = getattr(env, 'GITHUB_WEBHOOK_SECRET', None)
    
    if not secret:
        print('GITHUB_WEBHOOK_SECRET not configured')
        return True  # Allow in development
    
    # Use Web Crypto API for HMAC
    encoder = crypto.TextEncoder.new()
    key_data = encoder.encode(secret)
    
    key = await crypto.subtle.importKey(
        'raw',
        key_data,
        {'name': 'HMAC', 'hash': 'SHA-256'},
        False,
        ['sign']
    )
    
    signed = await crypto.subtle.sign('HMAC', key, encoder.encode(body))
    
    # Convert to hex string
    signed_array = crypto.Uint8Array.new(signed)
    hex_signature = 'sha256=' + ''.join([f'{b:02x}' for b in signed_array])
    
    return signature == hex_signature


async def handle_webhook(request, env):
    """Handle GitHub webhook"""
    # Verify signature
    is_valid = await verify_webhook_signature(request.clone(), env)
    if not is_valid:
        return Response.new('Invalid signature', status=401)
    
    event = request.headers.get('X-GitHub-Event')
    payload = json.loads(await request.text())
    
    try:
        if event == 'issues':
            await handle_issue_event(payload, env)
        elif event == 'ping':
            headers = Headers.new()
            headers.set('Content-Type', 'application/json')
            body = json.dumps({'message': 'Webhook configured successfully'})
            return Response.new(body, headers=headers)
        
        headers = Headers.new()
        headers.set('Content-Type', 'application/json')
        body = json.dumps({'status': 'processed'})
        return Response.new(body, headers=headers)
    except Exception as error:
        print(f'Webhook processing error: {error}')
        headers = Headers.new()
        headers.set('Content-Type', 'application/json')
        body = json.dumps({'error': str(error)})
        return Response.new(body, status=500, headers=headers)


async def handle_issue_event(payload, env):
    """Handle issue events"""
    issue = payload['issue']
    action = payload['action']
    repository = payload['repository']['full_name']
    
    print(f'Processing issue event: {action} for {repository}#{issue["number"]}')
    
    # Calculate time to close
    time_to_close = None
    if issue['state'] == 'closed' and issue.get('closed_at'):
        time_to_close = calculate_time_to_close(issue['created_at'], issue['closed_at'])
    
    # Upsert issue
    await env.DB.prepare('''
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
    ''').bind(
        issue['id'],
        issue['number'],
        issue['title'],
        issue.get('body', ''),
        issue['state'],
        issue['created_at'],
        issue['updated_at'],
        issue.get('closed_at'),
        issue['html_url'],
        repository,
        issue['assignee']['login'] if issue.get('assignee') else None,
        issue['milestone']['title'] if issue.get('milestone') else None,
        time_to_close
    ).run()
    
    # Update labels
    await env.DB.prepare('DELETE FROM labels WHERE issue_id = ?').bind(issue['id']).run()
    for label in issue.get('labels', []):
        await env.DB.prepare(
            'INSERT INTO labels (issue_id, name, color) VALUES (?, ?, ?)'
        ).bind(issue['id'], label['name'], label['color']).run()
    
    # Update assignees
    await env.DB.prepare('DELETE FROM assignees WHERE issue_id = ?').bind(issue['id']).run()
    for assignee in issue.get('assignees', []):
        await env.DB.prepare(
            'INSERT INTO assignees (issue_id, username) VALUES (?, ?)'
        ).bind(issue['id'], assignee['login']).run()
    
    # Update metrics
    await update_repository_metrics(repository, env)
