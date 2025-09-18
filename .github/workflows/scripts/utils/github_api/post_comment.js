const fs = require('fs');

async function postComment(github, context, body, issueNumber) {
  if (!body.trim()) {
    console.log('Comment body is empty, skipping post.');
    return;
  }

  if (!issueNumber) {
    console.warn('Unable to determine issue or PR number for comment.');
    return;
  }

  try {
    await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
      body: body,
    });
    console.log(`Successfully posted comment to issue/PR #${issueNumber}`);
  } catch (error) {
    console.error(`Failed to post comment: ${error.message}`);
    throw error;
  }
}

module.exports = { postComment };