module.exports = async ({ github, context, core }) => {
  const { eventName, payload, repo } = context;
  const owner = repo.owner;
  const repository = repo.repo;

  async function addIssueReaction(issueNumber) {
    if (!issueNumber) {
      core.warning('No issue or PR number found for reaction.');
      return;
    }
    await github.rest.reactions.createForIssue({
      owner,
      repo: repository,
      issue_number: issueNumber,
      content: 'eyes',
    });
  }

  async function addCommentReaction(commentId, type) {
    if (!commentId) {
      core.warning(`No ${type} comment id found for reaction.`);
      return;
    }
    const params = { owner, repo: repository, comment_id: commentId, content: 'eyes' };
    if (type === 'issue') {
      await github.rest.reactions.createForIssueComment(params);
    } else if (type === 'review') {
      await github.rest.reactions.createForPullRequestReviewComment(params);
    }
  }

  try {
    if (eventName === 'pull_request') {
      await addIssueReaction(payload.pull_request?.number);
    } else if (eventName === 'issue_comment') {
      await addCommentReaction(payload.comment?.id, 'issue');
    } else if (eventName === 'pull_request_review_comment') {
      await addCommentReaction(payload.comment?.id, 'review');
    } else {
      core.warning(`Unsupported event "${eventName}" for reaction step.`);
    }
  } catch (error) {
    core.warning(`Failed to add 👀 reaction: ${error.message}`);
  }
};
