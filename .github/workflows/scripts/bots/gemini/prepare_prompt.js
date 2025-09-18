const core = require('@actions/core');
const { context, getOctokit } = require('@actions/github');
const github = getOctokit(process.env.GITHUB_TOKEN);

const eventName = process.env.EVENT_NAME;
const payload = JSON.parse(process.env.EVENT_PAYLOAD || '{}');
const repoOwner = context.repo.owner;
const repoName = context.repo.repo;

const prNumber =
  eventName === 'pull_request'
    ? payload.pull_request?.number
    : payload.issue?.number ?? payload.pull_request?.number ?? null;

async function loadPullRequestContext(number) {
  if (!number) {
    return { pr: null, files: [], commits: [] };
  }
  try {
    const prResponse = await github.rest.pulls.get({
      owner: repoOwner,
      repo: repoName,
      pull_number: number,
    });
    const files = await github.paginate(github.rest.pulls.listFiles, {
      owner: repoOwner,
      repo: repoName,
      pull_number: number,
      per_page: 100,
    });
    const commits = await github.paginate(github.rest.pulls.listCommits, {
      owner: repoOwner,
      repo: repoName,
      pull_number: number,
      per_page: 100,
    });
    return { pr: prResponse.data, files, commits };
  } catch (error) {
    core.warning(`Failed to load pull request context: ${error.message}`);
    return { pr: null, files: [], commits: [] };
  }
}

function formatPatch(patch) {
  if (!patch) {
    return '';
  }
  const maxChars = 1500;
  let content = patch;
  if (content.length > maxChars) {
    content = `${content.slice(0, maxChars)}\n... (patch truncated)`;
  }
  return ['```diff', content, '```'].join('\n');
}

function formatFiles(files) {
  if (!files || files.length === 0) {
    return '_No changed files found._';
  }
  return files
    .map((file) => {
      const header = `- ${file.filename} (${file.status}, +${file.additions} / -${file.deletions})`;
      const patch = formatPatch(file.patch);
      return patch ? `${header}\n${patch}` : header;
    })
    .join('\n\n');
}

function formatCommits(commits) {
  if (!commits || commits.length === 0) {
    return '_No commits returned._';
  }
  return commits
    .map((commit) => `- ${commit.sha.slice(0, 7)} ${commit.commit.message.split('\n')[0]}`)
    .join('\n');
}

const { pr, files, commits } = await loadPullRequestContext(prNumber);

const descriptionSource =
  pr?.body ??
  payload.pull_request?.body ??
  payload.issue?.body ??
  '';
const description = descriptionSource?.trim();
const prDescription = description && description.length > 0 ? description : '_No description provided._';

const commentBody = payload.comment?.body?.trim();
const userRequest = commentBody && commentBody.length > 0 ? commentBody : null;

const prTitle =
  pr?.title ??
  payload.pull_request?.title ??
  payload.issue?.title ??
  'unknown';

const prAuthor =
  pr?.user?.login ??
  payload.pull_request?.user?.login ??
  payload.issue?.user?.login ??
  'unknown';

const prUrl =
  pr?.html_url ??
  payload.pull_request?.html_url ??
  payload.issue?.pull_request?.html_url ??
  payload.comment?.html_url ??
  '';

const rawIssueNumber = payload.pull_request?.number ?? payload.issue?.number ?? '';
const rawIssueTitle = payload.pull_request?.title ?? payload.issue?.title ?? '';
const rawIssueBody = payload.pull_request?.body ?? payload.issue?.body ?? '';
const commentBodyRaw = payload.comment?.body ?? '';

const sections = [
  'You are a meticulous senior engineer reviewing the following pull request. Provide a thorough analysis of the changes, highlighting intent, quality, and potential issues.',
  'Follow the Markdown response template exactly. Use concise bullet points under each heading, and write `- None noted.` when a section does not apply. Prioritize actionable feedback, missing tests, and blockers.',
  '',

  'Response template:',
  '📝 **Summary**',
  '✅ **Tests & Coverage**',
  '⚠️ **Risks & Regressions**',
  '💡 **Suggestions & Improvements**',
  '📌 **Follow-ups**',
  '🚫 **Blocking Issues**',
  '',

  'Guidelines:',
  '- Reference specific files, commits, or behaviors when possible.',
  '- Explicitly call out missing or insufficient tests.',
  '- Separate blocking issues (must fix before merge) from optional suggestions.',
  '',

  `Repository: ${repoOwner}/${repoName}`,
  `Pull Request: #${pr?.number ?? prNumber ?? 'unknown'}`,
  `Title: ${prTitle}`,
  `Author: ${prAuthor}`,
  `URL: ${prUrl}`,
  '',

  'Changed files:',
  formatFiles(files),
  '',

  'Recent commits:',
  formatCommits(commits),
  '',

  'Pull request description:',
  prDescription,
];

if (userRequest) {
  sections.push('', 'Additional request from comment:', userRequest);
}

const prompt = sections.join('\n');

core.setOutput('prompt', prompt);
core.setOutput('issue_number', `${rawIssueNumber || ''}`);
core.setOutput('issue_title', rawIssueTitle || '');
core.setOutput('issue_body', rawIssueBody || '');
core.setOutput('comment_body', commentBodyRaw || '');