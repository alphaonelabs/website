"""
API Handlers
"""

from js import Response, Headers, URL
import json
from github import sync_repository, update_github_issue, sync_issue


async def handle_get_issues(request, env, session, cors_headers):
    """Get issues with filtering and sorting"""
    url = URL.new(request.url)
    repository = url.searchParams.get('repository')
    state = url.searchParams.get('state') or 'all'
    label = url.searchParams.get('label')
    assignee = url.searchParams.get('assignee')
    sort_by = url.searchParams.get('sort') or 'updated_at'
    order = url.searchParams.get('order') or 'desc'
    page = int(url.searchParams.get('page') or '1')
    per_page = int(url.searchParams.get('per_page') or '50')
    
    try:
        # Build query
        query = 'SELECT DISTINCT i.* FROM issues i'
        conditions = []
        bindings = []
        
        if repository:
            conditions.append('i.repository = ?')
            bindings.append(repository)
        
        if state != 'all':
            conditions.append('i.state = ?')
            bindings.append(state)
        
        if label:
            query += ' INNER JOIN labels l ON i.id = l.issue_id'
            conditions.append('l.name = ?')
            bindings.append(label)
        
        if assignee:
            if assignee == 'none':
                conditions.append('i.assignee IS NULL')
            else:
                query += ' INNER JOIN assignees a ON i.id = a.issue_id'
                conditions.append('a.username = ?')
                bindings.append(assignee)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        # Add sorting
        valid_sort_fields = ['number', 'title', 'state', 'created_at', 'updated_at', 'closed_at', 'time_to_close']
        sort_field = sort_by if sort_by in valid_sort_fields else 'updated_at'
        sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'
        query += f' ORDER BY i.{sort_field} {sort_order}'
        
        # Add pagination
        offset = (page - 1) * per_page
        query += ' LIMIT ? OFFSET ?'
        bindings.extend([per_page, offset])
        
        # Execute query
        result = await env.DB.prepare(query).bind(*bindings).all()
        
        # Get labels and assignees for each issue
        for issue in result['results']:
            labels = await env.DB.prepare(
                'SELECT name, color FROM labels WHERE issue_id = ?'
            ).bind(issue['id']).all()
            issue['labels'] = labels['results']
            
            assignees = await env.DB.prepare(
                'SELECT username FROM assignees WHERE issue_id = ?'
            ).bind(issue['id']).all()
            issue['assignees'] = [a['username'] for a in assignees['results']]
        
        # Get total count
        count_query = 'SELECT COUNT(DISTINCT i.id) as total FROM issues i'
        if label:
            count_query += ' INNER JOIN labels l ON i.id = l.issue_id'
        if assignee and assignee != 'none':
            count_query += ' INNER JOIN assignees a ON i.id = a.issue_id'
        if conditions:
            count_query += ' WHERE ' + ' AND '.join(conditions)
        
        count_bindings = bindings[:-2]  # Remove LIMIT and OFFSET
        count_result = await env.DB.prepare(count_query).bind(*count_bindings).first()
        
        response_data = {
            'issues': result['results'],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': count_result['total'],
                'total_pages': (count_result['total'] + per_page - 1) // per_page
            }
        }
        
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        
        return Response.new(json.dumps(response_data), headers=headers)
    
    except Exception as error:
        print(f'Error fetching issues: {error}')
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': str(error)}), status=500, headers=headers)


async def handle_get_issue(request, env, session, issue_number, cors_headers):
    """Get single issue"""
    url = URL.new(request.url)
    repository = url.searchParams.get('repository')
    
    if not repository:
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': 'repository parameter required'}), status=400, headers=headers)
    
    try:
        issue = await env.DB.prepare(
            'SELECT * FROM issues WHERE repository = ? AND number = ?'
        ).bind(repository, issue_number).first()
        
        if not issue:
            headers = Headers.new()
            for key, value in cors_headers.items():
                headers.set(key, value)
            headers.set('Content-Type', 'application/json')
            return Response.new(json.dumps({'error': 'Issue not found'}), status=404, headers=headers)
        
        # Get labels and assignees
        labels = await env.DB.prepare(
            'SELECT name, color FROM labels WHERE issue_id = ?'
        ).bind(issue['id']).all()
        issue['labels'] = labels['results']
        
        assignees = await env.DB.prepare(
            'SELECT username FROM assignees WHERE issue_id = ?'
        ).bind(issue['id']).all()
        issue['assignees'] = [a['username'] for a in assignees['results']]
        
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        
        return Response.new(json.dumps(issue), headers=headers)
    
    except Exception as error:
        print(f'Error fetching issue: {error}')
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': str(error)}), status=500, headers=headers)


async def handle_update_issue(request, env, session, issue_number, cors_headers):
    """Update issue"""
    url = URL.new(request.url)
    repository = url.searchParams.get('repository')
    
    if not repository:
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': 'repository parameter required'}), status=400, headers=headers)
    
    try:
        updates = json.loads(await request.text())
        owner, repo = repository.split('/')
        
        # Update on GitHub
        updated_issue = await update_github_issue(owner, repo, issue_number, updates, session['accessToken'])
        
        # Sync back to database
        await sync_issue(updated_issue, repository, env)
        
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        
        return Response.new(json.dumps({'success': True, 'issue': updated_issue}), headers=headers)
    
    except Exception as error:
        print(f'Error updating issue: {error}')
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': str(error)}), status=500, headers=headers)


async def handle_bulk_update(request, env, session, cors_headers):
    """Bulk update issues"""
    try:
        data = json.loads(await request.text())
        repository = data.get('repository')
        issue_numbers = data.get('issue_numbers')
        updates = data.get('updates')
        
        if not repository or not issue_numbers or not updates:
            headers = Headers.new()
            for key, value in cors_headers.items():
                headers.set(key, value)
            headers.set('Content-Type', 'application/json')
            return Response.new(
                json.dumps({'error': 'repository, issue_numbers, and updates are required'}),
                status=400,
                headers=headers
            )
        
        owner, repo = repository.split('/')
        results = []
        
        for issue_number in issue_numbers:
            try:
                updated_issue = await update_github_issue(owner, repo, issue_number, updates, session['accessToken'])
                await sync_issue(updated_issue, repository, env)
                results.append({'issue_number': issue_number, 'success': True})
            except Exception as error:
                results.append({'issue_number': issue_number, 'success': False, 'error': str(error)})
        
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        
        return Response.new(json.dumps({'results': results}), headers=headers)
    
    except Exception as error:
        print(f'Error in bulk update: {error}')
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': str(error)}), status=500, headers=headers)


async def handle_sync_repository(request, env, session, cors_headers):
    """Sync repository"""
    try:
        data = json.loads(await request.text())
        repository = data.get('repository')
        
        if not repository:
            headers = Headers.new()
            for key, value in cors_headers.items():
                headers.set(key, value)
            headers.set('Content-Type', 'application/json')
            return Response.new(json.dumps({'error': 'repository parameter required'}), status=400, headers=headers)
        
        owner, repo = repository.split('/')
        result = await sync_repository(owner, repo, session['accessToken'], env)
        
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        
        return Response.new(json.dumps(result), headers=headers)
    
    except Exception as error:
        print(f'Error syncing repository: {error}')
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': str(error)}), status=500, headers=headers)
