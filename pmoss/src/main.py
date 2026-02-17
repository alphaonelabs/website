"""
OSS Project Management - Python Cloudflare Worker
Main entry point for the application
"""

from js import Response, Headers, URL, fetch
from auth import handle_auth, handle_auth_callback, verify_session
from webhook import handle_webhook
from api import (
    handle_get_issues,
    handle_get_issue,
    handle_update_issue,
    handle_bulk_update,
    handle_sync_repository
)
from metrics import handle_get_metrics
from ui import serve_ui
import json


def get_cors_headers():
    """Get CORS headers for API requests"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname
    method = request.method
    
    cors_headers = get_cors_headers()
    
    # Handle OPTIONS for CORS
    if method == 'OPTIONS':
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        return Response.new(None, status=200, headers=headers)
    
    try:
        # Public routes
        if path == '/':
            return serve_ui(env)
        
        if path == '/auth':
            return handle_auth(env)
        
        if path == '/auth/callback':
            return await handle_auth_callback(request, env)
        
        if path == '/webhook' and method == 'POST':
            return await handle_webhook(request, env)
        
        # Protected API routes
        session = await verify_session(request, env)
        if not session:
            headers = Headers.new()
            for key, value in cors_headers.items():
                headers.set(key, value)
            headers.set('Content-Type', 'application/json')
            body = json.dumps({'error': 'Unauthorized'})
            return Response.new(body, status=401, headers=headers)
        
        # API Routes
        if path == '/api/issues' and method == 'GET':
            return await handle_get_issues(request, env, session, cors_headers)
        
        if path.startswith('/api/issues/') and path != '/api/issues/bulk':
            issue_number = path.split('/')[-1]
            if issue_number.isdigit():
                if method == 'GET':
                    return await handle_get_issue(request, env, session, issue_number, cors_headers)
                elif method == 'PATCH':
                    return await handle_update_issue(request, env, session, issue_number, cors_headers)
        
        if path == '/api/issues/bulk' and method == 'PATCH':
            return await handle_bulk_update(request, env, session, cors_headers)
        
        if path == '/api/sync' and method == 'POST':
            return await handle_sync_repository(request, env, session, cors_headers)
        
        if path == '/api/metrics' and method == 'GET':
            return await handle_get_metrics(request, env, session, cors_headers)
        
        # 404 for unknown routes
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        return Response.new('Not Found', status=404, headers=headers)
    
    except Exception as error:
        print(f'Error handling request: {error}')
        headers = Headers.new()
        for key, value in cors_headers.items():
            headers.set(key, value)
        headers.set('Content-Type', 'application/json')
        body = json.dumps({
            'error': 'Internal Server Error',
            'message': str(error)
        })
        return Response.new(body, status=500, headers=headers)
