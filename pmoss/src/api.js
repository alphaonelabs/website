/**
 * API Handlers
 */

import { syncRepository, updateGitHubIssue, syncIssue } from './github';

/**
 * Get issues with filtering and sorting
 */
export async function handleGetIssues(request, env, session, corsHeaders) {
  const url = new URL(request.url);
  const repository = url.searchParams.get('repository');
  const state = url.searchParams.get('state') || 'all';
  const label = url.searchParams.get('label');
  const assignee = url.searchParams.get('assignee');
  const sortBy = url.searchParams.get('sort') || 'updated_at';
  const order = url.searchParams.get('order') || 'desc';
  const page = parseInt(url.searchParams.get('page') || '1');
  const perPage = parseInt(url.searchParams.get('per_page') || '50');

  try {
    // Build query
    let query = 'SELECT DISTINCT i.* FROM issues i';
    const conditions = [];
    const bindings = [];

    if (repository) {
      conditions.push('i.repository = ?');
      bindings.push(repository);
    }

    if (state !== 'all') {
      conditions.push('i.state = ?');
      bindings.push(state);
    }

    if (label) {
      query += ' INNER JOIN labels l ON i.id = l.issue_id';
      conditions.push('l.name = ?');
      bindings.push(label);
    }

    if (assignee) {
      if (assignee === 'none') {
        conditions.push('i.assignee IS NULL');
      } else {
        query += ' INNER JOIN assignees a ON i.id = a.issue_id';
        conditions.push('a.username = ?');
        bindings.push(assignee);
      }
    }

    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }

    // Add sorting
    const validSortFields = ['number', 'title', 'state', 'created_at', 'updated_at', 'closed_at', 'time_to_close'];
    const sortField = validSortFields.includes(sortBy) ? sortBy : 'updated_at';
    const sortOrder = order.toLowerCase() === 'asc' ? 'ASC' : 'DESC';
    query += ` ORDER BY i.${sortField} ${sortOrder}`;

    // Add pagination
    const offset = (page - 1) * perPage;
    query += ` LIMIT ? OFFSET ?`;
    bindings.push(perPage, offset);

    // Execute query
    const result = await env.DB.prepare(query).bind(...bindings).all();

    // Get labels and assignees for each issue
    for (const issue of result.results) {
      const labels = await env.DB.prepare(
        'SELECT name, color FROM labels WHERE issue_id = ?'
      ).bind(issue.id).all();
      issue.labels = labels.results;

      const assignees = await env.DB.prepare(
        'SELECT username FROM assignees WHERE issue_id = ?'
      ).bind(issue.id).all();
      issue.assignees = assignees.results.map(a => a.username);
    }

    // Get total count
    let countQuery = 'SELECT COUNT(DISTINCT i.id) as total FROM issues i';
    if (label) countQuery += ' INNER JOIN labels l ON i.id = l.issue_id';
    if (assignee && assignee !== 'none') countQuery += ' INNER JOIN assignees a ON i.id = a.issue_id';
    if (conditions.length > 0) {
      countQuery += ' WHERE ' + conditions.join(' AND ');
    }
    const countBindings = bindings.slice(0, bindings.length - 2); // Remove LIMIT and OFFSET
    const countResult = await env.DB.prepare(countQuery).bind(...countBindings).first();

    return new Response(JSON.stringify({
      issues: result.results,
      pagination: {
        page,
        per_page: perPage,
        total: countResult.total,
        total_pages: Math.ceil(countResult.total / perPage)
      }
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error fetching issues:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Get single issue
 */
export async function handleGetIssue(request, env, session, issueNumber, corsHeaders) {
  const url = new URL(request.url);
  const repository = url.searchParams.get('repository');

  if (!repository) {
    return new Response(JSON.stringify({ error: 'repository parameter required' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  try {
    const issue = await env.DB.prepare(
      'SELECT * FROM issues WHERE repository = ? AND number = ?'
    ).bind(repository, issueNumber).first();

    if (!issue) {
      return new Response(JSON.stringify({ error: 'Issue not found' }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Get labels and assignees
    const labels = await env.DB.prepare(
      'SELECT name, color FROM labels WHERE issue_id = ?'
    ).bind(issue.id).all();
    issue.labels = labels.results;

    const assignees = await env.DB.prepare(
      'SELECT username FROM assignees WHERE issue_id = ?'
    ).bind(issue.id).all();
    issue.assignees = assignees.results.map(a => a.username);

    return new Response(JSON.stringify(issue), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error fetching issue:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Update issue
 */
export async function handleUpdateIssue(request, env, session, issueNumber, corsHeaders) {
  const url = new URL(request.url);
  const repository = url.searchParams.get('repository');

  if (!repository) {
    return new Response(JSON.stringify({ error: 'repository parameter required' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  try {
    const updates = await request.json();
    const [owner, repo] = repository.split('/');

    // Update on GitHub
    const updatedIssue = await updateGitHubIssue(
      owner,
      repo,
      issueNumber,
      updates,
      session.accessToken
    );

    // Sync back to database
    await syncIssue(updatedIssue, repository, env);

    return new Response(JSON.stringify({ success: true, issue: updatedIssue }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error updating issue:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Bulk update issues
 */
export async function handleBulkUpdate(request, env, session, corsHeaders) {
  try {
    const { repository, issue_numbers, updates } = await request.json();

    if (!repository || !issue_numbers || !updates) {
      return new Response(JSON.stringify({ 
        error: 'repository, issue_numbers, and updates are required' 
      }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const [owner, repo] = repository.split('/');
    const results = [];

    for (const issueNumber of issue_numbers) {
      try {
        const updatedIssue = await updateGitHubIssue(
          owner,
          repo,
          issueNumber,
          updates,
          session.accessToken
        );
        await syncIssue(updatedIssue, repository, env);
        results.push({ issue_number: issueNumber, success: true });
      } catch (error) {
        results.push({ issue_number: issueNumber, success: false, error: error.message });
      }
    }

    return new Response(JSON.stringify({ results }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error in bulk update:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Sync repository
 */
export async function handleSyncRepository(request, env, session, corsHeaders) {
  try {
    const { repository } = await request.json();

    if (!repository) {
      return new Response(JSON.stringify({ error: 'repository parameter required' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const [owner, repo] = repository.split('/');
    const result = await syncRepository(owner, repo, session.accessToken, env);

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error syncing repository:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}
