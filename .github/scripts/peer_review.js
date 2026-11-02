// Keeps each open pull request's peer-review state visible:
//   - the "peer reviewed" label is on exactly the PRs with a current approval
//     from someone other than the author;
//   - PRs without one get a single reminder comment (removed once approved);
//   - newly opened PRs are announced in Slack so contributors can pick them up.
// Used by .github/workflows/peer-review-reminder.yml through actions/github-script.

const LABEL = 'peer reviewed';
const LABEL_COLOR = 'D4AF37';
const LABEL_DESCRIPTION = 'Approved by at least one peer (not the author)';
const MARKER = '<!-- peer-review-reminder -->';
const SLACK_INVITE = 'https://join.slack.com/t/alphaonelabs/shared_invite/zt-3glzypiib-8Lq~UZwWvcCFAjeG5uwcPg';
const EXEMPT_USERS = new Set([
  'A1L13N',
  'copilot-swe-agent[bot]',
  'copilot[bot]',
  'github-copilot[bot]',
  'dependabot[bot]',
]);

function isExempt(pr) {
  return EXEMPT_USERS.has(pr.user.login) || pr.head.ref.startsWith('copilot/');
}

// A reviewer's latest APPROVED/CHANGES_REQUESTED/DISMISSED review is their current
// verdict; plain comments don't change it.
function peerApprovers(reviews, author) {
  const latest = new Map();
  for (const review of reviews) {
    const login = review.user && review.user.login;
    if (!login || login === author || review.user.type === 'Bot') continue;
    if (!['APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'].includes(review.state)) continue;
    latest.set(login, review.state);
  }
  return [...latest].filter(([, state]) => state === 'APPROVED').map(([login]) => login);
}

async function ensureLabel(github, repo) {
  try {
    await github.rest.issues.getLabel({ ...repo, name: LABEL });
  } catch (error) {
    if (error.status !== 404) throw error;
    await github.rest.issues.createLabel({ ...repo, name: LABEL, color: LABEL_COLOR, description: LABEL_DESCRIPTION });
  }
}

function reminderBody(pr, channel) {
  const where = channel ? `the **${channel}** channel on [Slack](${SLACK_INVITE})` : `our [Slack](${SLACK_INVITE})`;
  return [
    MARKER,
    '## 👀 Peer review needed',
    '',
    `Hi @${pr.user.login}! This pull request doesn't have a **peer review** yet.`,
    '',
    'Before a maintainer reviews it, another contributor needs to review and approve it:',
    '',
    `- Share the link in ${where} and ask for a reviewer.`,
    '- Offer to review someone else\'s PR in return — that\'s how the queue keeps moving.',
    `- Once a peer approves, this PR gets the \`${LABEL}\` label and this comment is removed.`,
    '',
    'New commits clear existing approvals, so ask your reviewer to take another look after pushing changes.',
  ].join('\n');
}

async function notifySlack(core, pr) {
  const webhook = process.env.SLACK_PEER_REVIEW_WEBHOOK;
  if (!webhook) return;
  const text = `:eyes: *Peer review wanted:* <${pr.html_url}|#${pr.number} ${pr.title.replace(/[<>&]/g, '')}> by ${pr.user.login}. Reply in a thread if you're taking it.`;
  const response = await fetch(webhook, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, unfurl_links: false }),
  });
  if (!response.ok) core.warning(`Slack webhook returned ${response.status}`);
}

async function syncPullRequest({ github, core, repo, pr, announce }) {
  if (pr.state !== 'open' || pr.draft) {
    core.info(`#${pr.number} is ${pr.draft ? 'a draft' : pr.state}, skipping`);
    return;
  }

  const reviews = await github.paginate(github.rest.pulls.listReviews, { ...repo, pull_number: pr.number, per_page: 100 });
  const approvers = peerApprovers(reviews, pr.user.login);
  const hasPeerReview = approvers.length > 0;
  const labels = pr.labels.map((label) => label.name);

  if (hasPeerReview && !labels.includes(LABEL)) {
    await ensureLabel(github, repo);
    await github.rest.issues.addLabels({ ...repo, issue_number: pr.number, labels: [LABEL] });
  } else if (!hasPeerReview && labels.includes(LABEL)) {
    await github.rest.issues.removeLabel({ ...repo, issue_number: pr.number, name: LABEL });
  }

  if (isExempt(pr)) {
    core.info(`#${pr.number} by ${pr.user.login} is exempt from the reminder`);
    return;
  }

  const comments = await github.paginate(github.rest.issues.listComments, { ...repo, issue_number: pr.number, per_page: 100 });
  const reminder = comments.find((c) => c.user.login === 'github-actions[bot]' && c.body.includes(MARKER));

  if (hasPeerReview) {
    if (reminder) await github.rest.issues.deleteComment({ ...repo, comment_id: reminder.id });
    core.info(`#${pr.number} approved by ${approvers.join(', ')}`);
    return;
  }

  if (!reminder) {
    await github.rest.issues.createComment({
      ...repo,
      issue_number: pr.number,
      body: reminderBody(pr, process.env.SLACK_PEER_REVIEW_CHANNEL),
    });
  }
  if (announce) await notifySlack(core, pr);
  core.info(`#${pr.number} has no peer review yet`);
}

module.exports = async ({ github, context, core }) => {
  const repo = context.repo;
  const event = context.eventName;
  let prs = [];
  let announce = false;

  if (event === 'pull_request_target') {
    prs = [context.payload.pull_request];
    announce = ['opened', 'ready_for_review'].includes(context.payload.action);
  } else if (event === 'workflow_run') {
    // Review events from forks only get a read-only token, so they trigger a tiny
    // workflow and we pick the PR up here, where the token can write.
    const run = context.payload.workflow_run;
    const head = `${run.head_repository.owner.login}:${run.head_branch}`;
    prs = await github.paginate(github.rest.pulls.list, { ...repo, state: 'open', head, per_page: 100 });
  } else {
    prs = await github.paginate(github.rest.pulls.list, { ...repo, state: 'open', per_page: 100 });
  }

  // The check stays green either way: an approval arrives through a separate run,
  // so a red result here would linger after the PR was approved.
  for (const pr of prs) {
    try {
      await syncPullRequest({ github, core, repo, pr, announce });
    } catch (error) {
      core.warning(`#${pr.number}: ${error.message}`);
    }
  }
};

module.exports.peerApprovers = peerApprovers;
