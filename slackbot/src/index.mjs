// Alpha One Labs Slack bot.
//
// Watches the channels it's invited to for alphaonelabs pull request links.
// A link to an open PR without a peer approval gets a threaded reply that
// mentions the poster; an approved one gets a ✅ reaction.
//
// Secrets: SLACK_SIGNING_SECRET, SLACK_BOT_TOKEN, GITHUB_TOKEN (read-only).

const PR_LINK = /https?:\/\/github\.com\/alphaonelabs\/([A-Za-z0-9._-]+)\/pull\/(\d+)/g;
const MAX_LINKS_PER_MESSAGE = 3;
const PEER_LABEL = 'peer reviewed';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'GET' && url.pathname === '/') {
      return new Response('Alpha One Labs Slack bot is running.', { headers: { 'Content-Type': 'text/plain' } });
    }
    if (request.method !== 'POST' || url.pathname !== '/slack/events') {
      return new Response('Not found', { status: 404 });
    }
    if (!env.SLACK_SIGNING_SECRET || !env.SLACK_BOT_TOKEN) {
      return new Response('Slack bot is not configured', { status: 503 });
    }

    const body = await request.text();
    if (!(await verifySlackSignature(request, body, env.SLACK_SIGNING_SECRET))) {
      return new Response('Invalid signature', { status: 401 });
    }

    const payload = JSON.parse(body);
    if (payload.type === 'url_verification') {
      return new Response(payload.challenge, { headers: { 'Content-Type': 'text/plain' } });
    }
    // Slack retries when we're slow; the first delivery is already being handled.
    if (request.headers.get('X-Slack-Retry-Num')) {
      return new Response('ok');
    }
    if (payload.type === 'event_callback') {
      ctx.waitUntil(handleEvent(payload.event, env).catch((error) => console.error('[slackbot]', error)));
    }
    // Slack needs an answer within 3 seconds; the work continues in waitUntil.
    return new Response('ok');
  },
};

export async function verifySlackSignature(request, body, secret, now = Date.now()) {
  const timestamp = request.headers.get('X-Slack-Request-Timestamp');
  const signature = request.headers.get('X-Slack-Signature') || '';
  if (!timestamp || Math.abs(now / 1000 - Number(timestamp)) > 60 * 5) return false;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const mac = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`v0:${timestamp}:${body}`));
  const expected = 'v0=' + [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, '0')).join('');
  return timingSafeEqual(expected, signature);
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export function findPullRequestLinks(text) {
  const seen = new Map();
  for (const match of (text || '').matchAll(PR_LINK)) {
    const key = `${match[1]}#${match[2]}`;
    if (!seen.has(key)) seen.set(key, { repo: match[1], number: Number(match[2]) });
  }
  return [...seen.values()].slice(0, MAX_LINKS_PER_MESSAGE);
}

function isWatchedChannel(channel, env) {
  const allowed = (env.SLACK_CHANNEL_IDS || '').split(',').map((s) => s.trim()).filter(Boolean);
  return allowed.length === 0 || allowed.includes(channel);
}

async function handleEvent(event, env) {
  // Only fresh human messages: skip bots, edits, joins and other subtypes.
  if (!event || event.type !== 'message' || event.subtype || event.bot_id) return;
  if (!isWatchedChannel(event.channel, env)) return;
  const links = findPullRequestLinks(event.text);
  if (!links.length) return;

  const missing = [];
  let anyApproved = false;
  for (const link of links) {
    const status = await peerReviewStatus(link, env);
    if (!status || !status.open) continue;
    if (status.approved) anyApproved = true;
    else missing.push(status);
  }

  const thread = event.thread_ts || event.ts;
  if (missing.length) {
    const list = missing.map((pr) => `• <${pr.url}|#${pr.number} ${escapeSlack(pr.title)}> (by ${escapeSlack(pr.author)})`).join('\n');
    await slack(env, 'chat.postMessage', {
      channel: event.channel,
      thread_ts: thread,
      unfurl_links: false,
      text: `<@${event.user}> heads up: ${missing.length === 1 ? 'this pull request doesn\'t' : 'these pull requests don\'t'} have a peer review yet.\n${list}\n\nBefore a maintainer reviews, ask another contributor to review and *approve* it on GitHub. Once a peer approves, the PR gets the \`${PEER_LABEL}\` label. Reviewing someone else's PR in return keeps the queue moving.`,
    });
  } else if (anyApproved) {
    await slack(env, 'reactions.add', { channel: event.channel, timestamp: event.ts, name: 'white_check_mark' });
  }
}

export function hasPeerApproval(reviews, author) {
  const latest = new Map();
  for (const review of reviews) {
    const login = review.user && review.user.login;
    if (!login || login === author || review.user.type === 'Bot') continue;
    if (!['APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'].includes(review.state)) continue;
    latest.set(login, review.state);
  }
  return [...latest.values()].includes('APPROVED');
}

async function peerReviewStatus({ repo, number }, env) {
  const base = `https://api.github.com/repos/alphaonelabs/${repo}/pulls/${number}`;
  const pr = await github(base, env);
  if (!pr) return null;
  const status = {
    number,
    url: pr.html_url,
    title: pr.title,
    author: pr.user.login,
    open: pr.state === 'open' && !pr.draft,
  };
  // The label is set by the peer-review workflow; trust it and skip a call.
  if ((pr.labels || []).some((label) => label.name === PEER_LABEL)) return { ...status, approved: true };
  const reviews = await github(`${base}/reviews?per_page=100`, env);
  return { ...status, approved: hasPeerApproval(reviews || [], pr.user.login) };
}

async function github(url, env) {
  const headers = {
    Accept: 'application/vnd.github+json',
    'User-Agent': 'alphaonelabs-slackbot',
    'X-GitHub-Api-Version': '2022-11-28',
  };
  if (env.GITHUB_TOKEN) headers.Authorization = `Bearer ${env.GITHUB_TOKEN}`;
  const response = await fetch(url, { headers });
  if (!response.ok) {
    console.warn(`[slackbot] GitHub ${response.status} for ${url}`);
    return null;
  }
  return response.json();
}

async function slack(env, method, body) {
  const response = await fetch(`https://slack.com/api/${method}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.SLACK_BOT_TOKEN}`, 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!result.ok && result.error !== 'already_reacted') console.warn(`[slackbot] ${method}: ${result.error}`);
  return result;
}

function escapeSlack(text) {
  return String(text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
