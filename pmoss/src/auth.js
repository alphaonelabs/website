/**
 * GitHub OAuth Authentication
 */

const GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize';
const GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token';
const GITHUB_USER_URL = 'https://api.github.com/user';

/**
 * Initiate OAuth flow
 */
export async function handleAuth(env) {
  const params = new URLSearchParams({
    client_id: env.GITHUB_CLIENT_ID,
    redirect_uri: env.GITHUB_REDIRECT_URI || env.GITHUB_REDIRECT_URI_DEFAULT,
    scope: 'repo read:user',
    state: crypto.randomUUID()
  });

  const redirectUrl = `${GITHUB_AUTHORIZE_URL}?${params.toString()}`;
  
  return Response.redirect(redirectUrl, 302);
}

/**
 * Handle OAuth callback
 */
export async function handleAuthCallback(request, env) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  
  if (!code) {
    return new Response('Authorization failed: No code provided', { status: 400 });
  }

  try {
    // Exchange code for access token
    const tokenResponse = await fetch(GITHUB_TOKEN_URL, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: env.GITHUB_CLIENT_ID,
        client_secret: env.GITHUB_CLIENT_SECRET,
        code: code,
        redirect_uri: env.GITHUB_REDIRECT_URI || env.GITHUB_REDIRECT_URI_DEFAULT
      })
    });

    const tokenData = await tokenResponse.json();
    
    if (tokenData.error) {
      throw new Error(tokenData.error_description || tokenData.error);
    }

    const accessToken = tokenData.access_token;

    // Get user info
    const userResponse = await fetch(GITHUB_USER_URL, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Accept': 'application/json'
      }
    });

    const userData = await userResponse.json();

    // Create session
    const sessionId = crypto.randomUUID();
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days

    await env.DB.prepare(
      'INSERT INTO sessions (id, username, access_token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)'
    ).bind(
      sessionId,
      userData.login,
      accessToken,
      new Date().toISOString(),
      expiresAt.toISOString()
    ).run();

    // Set session cookie and redirect to home
    return new Response(null, {
      status: 302,
      headers: {
        'Location': '/',
        'Set-Cookie': `session=${sessionId}; HttpOnly; Secure; SameSite=Strict; Max-Age=${7 * 24 * 60 * 60}; Path=/`
      }
    });

  } catch (error) {
    console.error('Auth callback error:', error);
    return new Response(`Authentication failed: ${error.message}`, { status: 500 });
  }
}

/**
 * Verify session from request
 */
export async function verifySession(request, env) {
  const cookieHeader = request.headers.get('Cookie');
  if (!cookieHeader) {
    return null;
  }

  const cookies = Object.fromEntries(
    cookieHeader.split(';').map(c => {
      const [key, ...v] = c.trim().split('=');
      return [key, v.join('=')];
    })
  );

  const sessionId = cookies.session;
  if (!sessionId) {
    return null;
  }

  try {
    const result = await env.DB.prepare(
      'SELECT * FROM sessions WHERE id = ? AND expires_at > ?'
    ).bind(sessionId, new Date().toISOString()).first();

    if (!result) {
      return null;
    }

    return {
      id: result.id,
      username: result.username,
      accessToken: result.access_token
    };
  } catch (error) {
    console.error('Session verification error:', error);
    return null;
  }
}

/**
 * Get session token for Authorization header
 */
export function getAuthToken(request) {
  const authHeader = request.headers.get('Authorization');
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }
  return null;
}
