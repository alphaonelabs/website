"""
Metrics and Analytics Handler
"""

from js import Response, Headers, URL
import json


async def handle_get_metrics(request, env, session, cors_headers):
    """Get metrics for repository"""
    url = URL.new(request.url)
    repository = url.searchParams.get('repository')
    
    if not repository:
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': 'repository parameter required'}), status=400, headers=headers)
    
    try:
        # Current stats
        current_stats = await env.DB.prepare('''
            SELECT 
                COUNT(*) as total_issues,
                SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) as open_issues,
                SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) as closed_issues,
                AVG(CASE WHEN time_to_close IS NOT NULL THEN time_to_close END) as avg_time_to_close_hours,
                MIN(created_at) as oldest_issue_date,
                MAX(updated_at) as latest_update_date
            FROM issues WHERE repository = ?
        ''').bind(repository).first()
        
        # Label distribution
        label_stats = await env.DB.prepare('''
            SELECT l.name, l.color, COUNT(*) as count
            FROM labels l
            INNER JOIN issues i ON l.issue_id = i.id
            WHERE i.repository = ?
            GROUP BY l.name, l.color
            ORDER BY count DESC
            LIMIT 10
        ''').bind(repository).all()
        
        # Assignee stats
        assignee_stats = await env.DB.prepare('''
            SELECT a.username, COUNT(*) as assigned_issues,
                SUM(CASE WHEN i.state = 'open' THEN 1 ELSE 0 END) as open_assigned,
                SUM(CASE WHEN i.state = 'closed' THEN 1 ELSE 0 END) as closed_assigned
            FROM assignees a
            INNER JOIN issues i ON a.issue_id = i.id
            WHERE i.repository = ?
            GROUP BY a.username
            ORDER BY assigned_issues DESC
            LIMIT 10
        ''').bind(repository).all()
        
        # Historical metrics (last 30 days)
        historical_metrics = await env.DB.prepare('''
            SELECT metric_date, total_issues, open_issues, closed_issues, avg_time_to_close
            FROM metrics
            WHERE repository = ?
            ORDER BY metric_date DESC
            LIMIT 30
        ''').bind(repository).all()
        
        # Time to close distribution
        time_to_close_distribution = await env.DB.prepare('''
            SELECT 
                CASE 
                    WHEN time_to_close < 24 THEN '< 1 day'
                    WHEN time_to_close < 168 THEN '1-7 days'
                    WHEN time_to_close < 720 THEN '1-4 weeks'
                    ELSE '> 4 weeks'
                END as bucket,
                COUNT(*) as count
            FROM issues
            WHERE repository = ? AND time_to_close IS NOT NULL
            GROUP BY bucket
        ''').bind(repository).all()
        
        # Issue velocity (issues opened/closed per day, last 7 days)
        velocity = await env.DB.prepare('''
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as opened
            FROM issues
            WHERE repository = ? AND created_at >= date('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        ''').bind(repository).all()
        
        closed_velocity = await env.DB.prepare('''
            SELECT 
                DATE(closed_at) as date,
                COUNT(*) as closed
            FROM issues
            WHERE repository = ? AND closed_at >= date('now', '-7 days') AND state = 'closed'
            GROUP BY DATE(closed_at)
            ORDER BY date DESC
        ''').bind(repository).all()
        
        # Build response
        avg_time_hours = current_stats.get('avg_time_to_close_hours')
        avg_time_days = round(avg_time_hours / 24, 1) if avg_time_hours else None
        
        response_data = {
            'current': {
                **current_stats,
                'avg_time_to_close_days': str(avg_time_days) if avg_time_days else None
            },
            'labels': label_stats['results'],
            'assignees': assignee_stats['results'],
            'historical': list(reversed(historical_metrics['results'])),
            'time_to_close_distribution': time_to_close_distribution['results'],
            'velocity': {
                'opened': velocity['results'],
                'closed': closed_velocity['results']
            }
        }
        
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        
        return Response.new(json.dumps(response_data), headers=headers)
    
    except Exception as error:
        print(f'Error fetching metrics: {error}')
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        return Response.new(json.dumps({'error': str(error)}), status=500, headers=headers)
