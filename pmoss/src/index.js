/**
 * OSS Project Management - Cloudflare Worker
 * Main entry point for the application
 */

import { handleAuth, handleAuthCallback, verifySession } from './auth';
import { handleWebhook } from './webhook';
import { 
  handleGetIssues, 
  handleGetIssue, 
  handleUpdateIssue,
  handleBulkUpdate,
  handleSyncRepository
} from './api';
import { handleGetMetrics } from './metrics';
import { serveUI } from './ui';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers for API requests
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };

    // Handle OPTIONS for CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // Public routes
      if (path === '/') {
        return serveUI(env);
      }

      if (path === '/auth') {
        return handleAuth(env);
      }

      if (path === '/auth/callback') {
        return handleAuthCallback(request, env);
      }

      if (path === '/webhook' && request.method === 'POST') {
        return handleWebhook(request, env);
      }

      // Protected API routes
      const session = await verifySession(request, env);
      if (!session) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 401,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      // API Routes
      if (path === '/api/issues' && request.method === 'GET') {
        return handleGetIssues(request, env, session, corsHeaders);
      }

      if (path.match(/^\/api\/issues\/\d+$/) && request.method === 'GET') {
        const issueNumber = path.split('/').pop();
        return handleGetIssue(request, env, session, issueNumber, corsHeaders);
      }

      if (path.match(/^\/api\/issues\/\d+$/) && request.method === 'PATCH') {
        const issueNumber = path.split('/').pop();
        return handleUpdateIssue(request, env, session, issueNumber, corsHeaders);
      }

      if (path === '/api/issues/bulk' && request.method === 'PATCH') {
        return handleBulkUpdate(request, env, session, corsHeaders);
      }

      if (path === '/api/sync' && request.method === 'POST') {
        return handleSyncRepository(request, env, session, corsHeaders);
      }

      if (path === '/api/metrics' && request.method === 'GET') {
        return handleGetMetrics(request, env, session, corsHeaders);
      }

      // 404 for unknown routes
      return new Response('Not Found', { 
        status: 404,
        headers: corsHeaders 
      });

    } catch (error) {
      console.error('Error handling request:', error);
      return new Response(JSON.stringify({ 
        error: 'Internal Server Error',
        message: error.message 
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
