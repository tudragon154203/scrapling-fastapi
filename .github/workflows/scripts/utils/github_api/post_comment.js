const fs = require('fs');
const core = require('@actions/core');

async function postComment(github, context, body, issueNumber) {
  if (!body.trim()) {
    core.info('Comment body is empty, skipping post.');
    return;
  }

  if (!issueNumber) {
    core.warning('Unable to determine issue or PR number for comment.');
    return;
  }

  try {
    await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
      body: body,
    });
    core.info(`Successfully posted comment to issue/PR #${issueNumber}`);
  } catch (error) {
    core.error(`Failed to post comment: ${error.message}`);
    throw error;
  }
}

module.exports = { postComment };