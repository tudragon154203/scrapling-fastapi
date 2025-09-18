import core from '@actions/core';
import { context, getOctokit } from '@actions/github';

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
    core.warning(`Failed to load pull request context: ${error instanceof Error ? error.message : String(error)}`);
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

async function main() {
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
    'You are a meticulous senior engineer reviewing the following pull request. Provide a thorough, opinionated analysis that weighs intent, code quality, tests, and user impact. If information is missing, call it out explicitly.',
    'Follow the Markdown response template exactly. Each section must start with the provided heading and contain concise bullet points. Begin every bullet with an emoji indicator (`✅`, `⚠️`, `❌`, `💡`, etc.) that matches the tone of the observation.',
    'Use `- ✅ None noted.` when a section does not apply. Keep focus on the highest-impact issues, missing coverage, and user-facing risks.',
    'When referencing code, use backticked paths like `path/to/file.py` and include a short justification. Highlight blocking issues with **Action Required** and optional ideas with **Suggestion**.',
    '',

    'Response template (use these exact headings):',
    '### 🧭 Overall Verdict',
    '### 📝 Summary',
    '### 🧪 Tests & Coverage',
    '### ⚠️ Risks & Regressions',
    '### 💡 Suggestions & Improvements',
    '### 🔁 Follow-ups',
    '### 🚫 Blocking Issues',
    '',

    'Guidelines:',
    '- Lead with the overall assessment (approve, needs work, or blocked) in the Overall Verdict section.',
    '- Explicitly call out missing or insufficient tests in the Tests & Coverage section.',
    '- Separate must-fix items (Blocking Issues) from optional improvements (Suggestions & Improvements).',
    '- Limit each section to the most relevant points and avoid repeating information across sections.',
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
}

try {
  await main();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  core.setFailed(`prepare_prompt failed: ${message}`);
}
