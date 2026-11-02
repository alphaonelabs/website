import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker, { findPullRequestLinks, hasPeerApproval, verifySlackSignature } from '../src/index.mjs';

const SECRET = 'test-signing-secret';

async function sign(body, timestamp) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const mac = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`v0:${timestamp}:${body}`));
  return 'v0=' + [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function slackRequest(payload, { timestamp = Math.floor(Date.now() / 1000), badSig = false } = {}) {
  const body = JSON.stringify(payload);
  const signature = badSig ? 'v0=deadbeef' : await sign(body, timestamp);
  return new Request('https://slackbot.alphaonelabs.com/slack/events', {
    method: 'POST',
    headers: { 'X-Slack-Request-Timestamp': String(timestamp), 'X-Slack-Signature': signature },
    body,
  });
}

function runWorker(request, env, fetchImpl) {
  const pending = [];
  const calls = [];
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => { calls.push({ url: String(url), init }); return fetchImpl(String(url), init); };
  const ctx = { waitUntil: (p) => pending.push(p) };
  return worker.fetch(request, env, ctx)
    .then(async (response) => { await Promise.all(pending); return { response, calls }; })
    .finally(() => { globalThis.fetch = realFetch; });
}

const env = { SLACK_SIGNING_SECRET: SECRET, SLACK_BOT_TOKEN: 'xoxb-test', GITHUB_TOKEN: 'gh-test', SLACK_CHANNEL_IDS: '' };
const json = (data) => new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } });
const pr = (extra = {}) => ({ html_url: 'https://github.com/alphaonelabs/website/pull/12', title: 'Fix <thing>', user: { login: 'author' }, state: 'open', draft: false, labels: [], ...extra });
const message = (text, extra = {}) => ({ type: 'event_callback', event: { type: 'message', channel: 'C1', user: 'U1', ts: '1.0', text, ...extra } });

test('finds unique alphaonelabs PR links only', () => {
  const text = '<https://github.com/alphaonelabs/website/pull/12> and https://github.com/alphaonelabs/website/pull/12 plus https://github.com/other/repo/pull/3 and https://github.com/alphaonelabs/.github/pull/4';
  assert.deepEqual(findPullRequestLinks(text), [{ repo: 'website', number: 12 }, { repo: '.github', number: 4 }]);
});

test('peer approval uses each reviewer\'s latest verdict and ignores the author and bots', () => {
  const r = (login, state, type = 'User') => ({ user: { login, type }, state });
  assert.equal(hasPeerApproval([r('author', 'APPROVED')], 'author'), false);
  assert.equal(hasPeerApproval([r('bot', 'APPROVED', 'Bot')], 'author'), false);
  assert.equal(hasPeerApproval([r('peer', 'APPROVED'), r('peer', 'COMMENTED')], 'author'), true);
  assert.equal(hasPeerApproval([r('peer', 'APPROVED'), r('peer', 'DISMISSED')], 'author'), false);
});

test('rejects bad and stale signatures', async () => {
  const now = Math.floor(Date.now() / 1000);
  const good = await slackRequest({ a: 1 }, { timestamp: now });
  assert.equal(await verifySlackSignature(good, JSON.stringify({ a: 1 }), SECRET), true);
  const bad = await slackRequest({ a: 1 }, { badSig: true });
  assert.equal(await verifySlackSignature(bad, JSON.stringify({ a: 1 }), SECRET), false);
  const stale = await slackRequest({ a: 1 }, { timestamp: now - 600 });
  assert.equal(await verifySlackSignature(stale, JSON.stringify({ a: 1 }), SECRET), false);
  const { response } = await runWorker(bad, env, () => json({}));
  assert.equal(response.status, 401);
});

test('answers the URL verification challenge', async () => {
  const { response } = await runWorker(await slackRequest({ type: 'url_verification', challenge: 'abc' }), env, () => json({}));
  assert.equal(await response.text(), 'abc');
});

test('replies in thread and mentions the poster when a PR has no peer review', async () => {
  const { calls } = await runWorker(await slackRequest(message('please review https://github.com/alphaonelabs/website/pull/12')), env, (url) => {
    if (url.endsWith('/pulls/12')) return json(pr());
    if (url.includes('/reviews')) return json([{ user: { login: 'author', type: 'User' }, state: 'APPROVED' }]);
    return json({ ok: true });
  });
  const post = calls.find((c) => c.url.endsWith('chat.postMessage'));
  assert.ok(post, 'posted a reply');
  const body = JSON.parse(post.init.body);
  assert.equal(body.thread_ts, '1.0');
  assert.match(body.text, /<@U1>/);
  assert.match(body.text, /Fix &lt;thing&gt;/);
  assert.equal(calls.find((c) => c.url.includes('api.github.com')).init.headers.Authorization, 'Bearer gh-test');
});

test('reacts instead of replying when the PR is already peer reviewed', async () => {
  const { calls } = await runWorker(await slackRequest(message('https://github.com/alphaonelabs/website/pull/12')), env, (url) => {
    if (url.endsWith('/pulls/12')) return json(pr({ labels: [{ name: 'peer reviewed' }] }));
    return json({ ok: true });
  });
  assert.ok(calls.some((c) => c.url.endsWith('reactions.add')));
  assert.ok(!calls.some((c) => c.url.endsWith('chat.postMessage')));
  assert.ok(!calls.some((c) => c.url.includes('/reviews')), 'label short-circuits the reviews call');
});

test('ignores bots, edits, closed PRs, retries and unwatched channels', async () => {
  const handler = (url) => (url.endsWith('/pulls/12') ? json(pr({ state: 'closed' })) : json({ ok: true }));
  const link = 'https://github.com/alphaonelabs/website/pull/12';
  for (const payload of [
    message(link, { bot_id: 'B1' }),
    message(link, { subtype: 'message_changed' }),
    message(link),
  ]) {
    const { calls } = await runWorker(await slackRequest(payload), env, handler);
    assert.ok(!calls.some((c) => c.url.includes('slack.com')));
  }
  const { calls } = await runWorker(await slackRequest(message(link)), { ...env, SLACK_CHANNEL_IDS: 'C9' }, handler);
  assert.equal(calls.length, 0);
  const retry = await slackRequest(message(link));
  retry.headers.set('X-Slack-Retry-Num', '1');
  assert.equal((await runWorker(retry, env, handler)).calls.length, 0);
});

test('returns 503 until configured', async () => {
  const { response } = await runWorker(await slackRequest(message('x')), {}, () => json({}));
  assert.equal(response.status, 503);
});
