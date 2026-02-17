"""
GitHub API Client
"""

from js import fetch, Headers
import json
from datetime import datetime


GITHUB_API_BASE = 'https://api.github.com'


async def github_request(path, access_token, options=None):
    """Make authenticated GitHub API request"""
    if options is None:
        options = {}
    
    headers = Headers.new()
    headers.set('Authorization', f'Bearer {access_token}')
    headers.set('Accept', 'application/vnd.github.v3+json')
    headers.set('User-Agent', 'OSS-Project-Management')
    
    if 'headers' in options:
        for key, value in options['headers'].items():
            headers.set(key, value)
    
    fetch_options = {'headers': headers}
    if 'method' in options:
        fetch_options['method'] = options['method']
    if 'body' in options:
        fetch_options['body'] = options['body']
    
    response = await fetch(f'{GITHUB_API_BASE}{path}', fetch_options)
    
    if not response.ok:
        error_text = await response.text()
        raise Exception(f'GitHub API error: {response.status} {error_text}')
    
    return json.loads(await response.text())


async def fetch_repository_issues(owner, repo, access_token, state='all'):
    """Fetch all issues from a repository"""
    issues = []
    page = 1
    per_page = 100
    
    while True:
        data = await github_request(
            f'/repos/{owner}/{repo}/issues?state={state}&per_page={per_page}&page={page}',
            access_token
        )
        
        if len(data) == 0:
            break
        
        # Filter out pull requests
        actual_issues = [item for item in data if 'pull_request' not in item]
        issues.extend(actual_issues)
        
        if len(data) < per_page:
            break
        page += 1
    
    return issues


async def sync_repository(owner, repo, access_token, env):
    """Sync issues from GitHub to database"""
    repository = f'{owner}/{repo}'
    
    try:
        # Update sync status
        await env.DB.prepare('''
            INSERT INTO sync_status (repository, last_sync, status)
            VALUES (?, ?, 'in_progress')
            ON CONFLICT(repository) DO UPDATE SET
                last_sync = excluded.last_sync,
                status = 'in_progress',
                error_message = NULL
        ''').bind(repository, datetime.utcnow().isoformat()).run()
        
        # Fetch all issues
        issues = await fetch_repository_issues(owner, repo, access_token)
        
        # Store in database
        for issue in issues:
            await sync_issue(issue, repository, env)
        
        # Update sync status
        await env.DB.prepare(
            'UPDATE sync_status SET status = ?, last_sync = ? WHERE repository = ?'
        ).bind('completed', datetime.utcnow().isoformat(), repository).run()
        
        # Update metrics
        await update_repository_metrics(repository, env)
        
        return {'success': True, 'count': len(issues)}
    except Exception as error:
        # Update sync status with error
        await env.DB.prepare(
            'UPDATE sync_status SET status = ?, error_message = ? WHERE repository = ?'
        ).bind('failed', str(error), repository).run()
        
        raise error


async def sync_issue(issue, repository, env):
    """Sync single issue to database"""
    time_to_close = None
    if issue['state'] == 'closed' and issue.get('closed_at'):
        time_to_close = calculate_time_to_close(issue['created_at'], issue['closed_at'])
    
    # Insert or update issue
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


async def update_github_issue(owner, repo, issue_number, updates, access_token):
    """Update issue on GitHub"""
    return await github_request(
        f'/repos/{owner}/{repo}/issues/{issue_number}',
        access_token,
        {
            'method': 'PATCH',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(updates)
        }
    )


def calculate_time_to_close(created_at, closed_at):
    """Calculate time to close in hours"""
    created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    closed = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
    delta = closed - created
    return round(delta.total_seconds() / 3600)  # hours


async def update_repository_metrics(repository, env):
    """Update repository metrics"""
    today = datetime.utcnow().date().isoformat()
    
    stats = await env.DB.prepare('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) as open,
            SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) as closed,
            AVG(CASE WHEN time_to_close IS NOT NULL THEN time_to_close END) as avg_time
        FROM issues WHERE repository = ?
    ''').bind(repository).first()
    
    await env.DB.prepare('''
        INSERT INTO metrics (repository, metric_date, total_issues, open_issues, closed_issues, avg_time_to_close)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(repository, metric_date) DO UPDATE SET
            total_issues = excluded.total_issues,
            open_issues = excluded.open_issues,
            closed_issues = excluded.closed_issues,
            avg_time_to_close = excluded.avg_time_to_close
    ''').bind(
        repository,
        today,
        stats['total'] or 0,
        stats['open'] or 0,
        stats['closed'] or 0,
        stats['avg_time'] or 0
    ).run()
