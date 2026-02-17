/**
 * Metrics and Analytics Handler
 */

/**
 * Get metrics for repository
 */
export async function handleGetMetrics(request, env, session, corsHeaders) {
  const url = new URL(request.url);
  const repository = url.searchParams.get('repository');

  if (!repository) {
    return new Response(JSON.stringify({ error: 'repository parameter required' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  try {
    // Current stats
    const currentStats = await env.DB.prepare(`
      SELECT 
        COUNT(*) as total_issues,
        SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) as open_issues,
        SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) as closed_issues,
        AVG(CASE WHEN time_to_close IS NOT NULL THEN time_to_close END) as avg_time_to_close_hours,
        MIN(created_at) as oldest_issue_date,
        MAX(updated_at) as latest_update_date
      FROM issues WHERE repository = ?
    `).bind(repository).first();

    // Label distribution
    const labelStats = await env.DB.prepare(`
      SELECT l.name, l.color, COUNT(*) as count
      FROM labels l
      INNER JOIN issues i ON l.issue_id = i.id
      WHERE i.repository = ?
      GROUP BY l.name, l.color
      ORDER BY count DESC
      LIMIT 10
    `).bind(repository).all();

    // Assignee stats
    const assigneeStats = await env.DB.prepare(`
      SELECT a.username, COUNT(*) as assigned_issues,
        SUM(CASE WHEN i.state = 'open' THEN 1 ELSE 0 END) as open_assigned,
        SUM(CASE WHEN i.state = 'closed' THEN 1 ELSE 0 END) as closed_assigned
      FROM assignees a
      INNER JOIN issues i ON a.issue_id = i.id
      WHERE i.repository = ?
      GROUP BY a.username
      ORDER BY assigned_issues DESC
      LIMIT 10
    `).bind(repository).all();

    // Historical metrics (last 30 days)
    const historicalMetrics = await env.DB.prepare(`
      SELECT metric_date, total_issues, open_issues, closed_issues, avg_time_to_close
      FROM metrics
      WHERE repository = ?
      ORDER BY metric_date DESC
      LIMIT 30
    `).bind(repository).all();

    // Time to close distribution
    const timeToCloseDistribution = await env.DB.prepare(`
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
    `).bind(repository).all();

    // Issue velocity (issues opened/closed per day, last 7 days)
    const velocity = await env.DB.prepare(`
      SELECT 
        DATE(created_at) as date,
        COUNT(*) as opened
      FROM issues
      WHERE repository = ? AND created_at >= date('now', '-7 days')
      GROUP BY DATE(created_at)
      ORDER BY date DESC
    `).bind(repository).all();

    const closedVelocity = await env.DB.prepare(`
      SELECT 
        DATE(closed_at) as date,
        COUNT(*) as closed
      FROM issues
      WHERE repository = ? AND closed_at >= date('now', '-7 days') AND state = 'closed'
      GROUP BY DATE(closed_at)
      ORDER BY date DESC
    `).bind(repository).all();

    return new Response(JSON.stringify({
      current: {
        ...currentStats,
        avg_time_to_close_days: currentStats.avg_time_to_close_hours 
          ? (currentStats.avg_time_to_close_hours / 24).toFixed(1)
          : null
      },
      labels: labelStats.results,
      assignees: assigneeStats.results,
      historical: historicalMetrics.results.reverse(),
      time_to_close_distribution: timeToCloseDistribution.results,
      velocity: {
        opened: velocity.results,
        closed: closedVelocity.results
      }
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error fetching metrics:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}
