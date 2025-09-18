const fs = require('fs');

async function postComment(github, context, body, issueNumber) {
  console.log(`Attempting to post comment to issue/PR #${issueNumber}`);
  console.log(`Body length: ${body.length}`);
  console.log(`Body preview: ${body.substring(0, 200)}...`); // Log first 200 chars for debug

  if (!body.trim()) {
    console.log('Comment body is empty, skipping post.');
    return;
  }

  if (!issueNumber) {
    console.warn('Unable to determine issue or PR number for comment.');
    return;
  }

  try {
    const response = await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
      body: body,
    });
    console.log(`Successfully posted comment to issue/PR #${issueNumber}. Response: ${JSON.stringify(response.data, null, 2)}`);
  } catch (error) {
    console.error(`Failed to post comment: ${error.message}`);
    console.error(`Error details: ${JSON.stringify(error, null, 2)}`);
    throw error;
  }
}

module.exports = { postComment };