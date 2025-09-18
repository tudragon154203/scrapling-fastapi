import core from '@actions/core';
import { getOctokit, context } from '@actions/github';

const github = getOctokit(process.env.GITHUB_TOKEN);

async function run() {
  try {
    const payload = JSON.parse(process.env.EVENT_PAYLOAD || '{}');
    const issueNumber = payload.issue?.number ?? payload.pull_request?.number;
    const status = process.env.GEMINI_STATUS ?? 'unknown';

    if (!issueNumber) {
      core.info('No issue or pull request number found; skipping comment.');
      return;
    }

    const parts = [];
    if (process.env.GEMINI_SUMMARY) {
      parts.push('## Gemini Review\n\n' + process.env.GEMINI_SUMMARY);
    }
    if (process.env.GEMINI_ERROR) {
      parts.push('## Gemini Error\n\n```\n' + process.env.GEMINI_ERROR + '\n```');
    }
    if (status !== 'success') {
      parts.push(`Gemini CLI step ended with status: **${status}**.`);
    }

    const body = parts.join('\n\n').trim();
    if (!body) {
      core.info('No Gemini output to post.');
      return;
    }

    await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
      body,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    core.setFailed(`post_response failed: ${message}`);
  }
}

await run();
