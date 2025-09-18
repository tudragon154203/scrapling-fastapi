const core = require('@actions/core');
const { getOctokit, context } = require('@actions/github');
const github = getOctokit(process.env.GITHUB_TOKEN);

async function run() {
  try {
    const payload = JSON.parse(process.env.EVENT_PAYLOAD || '{}');
    const issueNumber = payload.issue?.number ?? payload.pull_request?.number;
    const status = process.env.GEMINI_STATUS ?? 'unknown';
    const parts = [];
    if (process.env.GEMINI_SUMMARY) {
      parts.push('## 🤖 Gemini Review\n\n' + process.env.GEMINI_SUMMARY);
    }
    if (process.env.GEMINI_ERROR) {
      parts.push('## ❗ Gemini Error\n\n```\n' + process.env.GEMINI_ERROR + '\n```');
    }
    if (status !== 'success') {
      parts.push(`⚠️ _Gemini CLI step ended with status: **${status}**._`);
    }
    const body = parts.join('\n\n').trim();
    await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
      body: body
    });
  } catch (error) {
    core.setFailed(error.message);
  }
}

run();