"""
GitHub OAuth Authentication
"""

from js import Response, Headers, URL, fetch, crypto
import json
from datetime import datetime, timedelta
import uuid


GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'


async def handle_auth(env):
    """Initiate OAuth flow"""
    state = str(uuid.uuid4())
    redirect_uri = getattr(env, 'GITHUB_REDIRECT_URI', '') or getattr(env, 'GITHUB_REDIRECT_URI_DEFAULT', '')
    
    params = {
        'client_id': env.GITHUB_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': 'repo read:user',
        'state': state
    }
    
    param_str = '&'.join([f'{k}={v}' for k, v in params.items()])
    redirect_url = f'{GITHUB_AUTHORIZE_URL}?{param_str}'
    
    headers = Headers.new()
    headers.set('Location', redirect_url)
    return Response.new(None, status=302, headers=headers)


async def handle_auth_callback(request, env):
    """Handle OAuth callback"""
    url = URL.new(request.url)
    code = url.searchParams.get('code')
    
    if not code:
        return Response.new('Authorization failed: No code provided', status=400)
    
    try:
        redirect_uri = getattr(env, 'GITHUB_REDIRECT_URI', '') or getattr(env, 'GITHUB_REDIRECT_URI_DEFAULT', '')
        
        # Exchange code for access token
        token_body = json.dumps({
            'client_id': env.GITHUB_CLIENT_ID,
            'client_secret': env.GITHUB_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri
        })
        
        token_headers = Headers.new()
        token_headers.set('Accept', 'application/json')
        token_headers.set('Content-Type', 'application/json')
        
        token_response = await fetch(GITHUB_TOKEN_URL, {
            'method': 'POST',
            'headers': token_headers,
            'body': token_body
        })
        
        token_data = json.loads(await token_response.text())
        
        if 'error' in token_data:
            raise Exception(token_data.get('error_description', token_data['error']))
        
        access_token = token_data['access_token']
        
        # Get user info
        user_headers = Headers.new()
        user_headers.set('Authorization', f'Bearer {access_token}')
        user_headers.set('Accept', 'application/json')
        
        user_response = await fetch(GITHUB_USER_URL, {'headers': user_headers})
        user_data = json.loads(await user_response.text())
        
        # Create session
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        await env.DB.prepare(
            'INSERT INTO sessions (id, username, access_token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)'
        ).bind(
            session_id,
            user_data['login'],
            access_token,
            datetime.utcnow().isoformat(),
            expires_at.isoformat()
        ).run()
        
        # Set session cookie and redirect
        headers = Headers.new()
        headers.set('Location', '/')
        cookie_value = f'session={session_id}; HttpOnly; Secure; SameSite=Strict; Max-Age={7 * 24 * 60 * 60}; Path=/'
        headers.set('Set-Cookie', cookie_value)
        
        return Response.new(None, status=302, headers=headers)
    
    except Exception as error:
        print(f'Auth callback error: {error}')
        return Response.new(f'Authentication failed: {str(error)}', status=500)


async def verify_session(request, env):
    """Verify session from request"""
    cookie_header = request.headers.get('Cookie')
    if not cookie_header:
        return None
    
    # Parse cookies
    cookies = {}
    for cookie in cookie_header.split(';'):
        if '=' in cookie:
            key, value = cookie.strip().split('=', 1)
            cookies[key] = value
    
    session_id = cookies.get('session')
    if not session_id:
        return None
    
    try:
        result = await env.DB.prepare(
            'SELECT * FROM sessions WHERE id = ? AND expires_at > ?'
        ).bind(session_id, datetime.utcnow().isoformat()).first()
        
        if not result:
            return None
        
        return {
            'id': result['id'],
            'username': result['username'],
            'accessToken': result['access_token']
        }
    except Exception as error:
        print(f'Session verification error: {error}')
        return None


def get_auth_token(request):
    """Get session token for Authorization header"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None
