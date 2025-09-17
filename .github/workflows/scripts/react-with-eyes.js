module.exports = async ({
  github,
  context,
  core,
  allowedCommentPrefixes = [],
}) => {
  const { eventName, payload, repo } = context;
  const owner = repo.owner;
  const repository = repo.repo;

  const normalizedPrefixes = Array.isArray(allowedCommentPrefixes)
    ? allowedCommentPrefixes
        .map((prefix) => (typeof prefix === 'string' ? prefix.trim().toLowerCase() : ''))
        .filter(Boolean)
    : [];

  function shouldReactToComment(commentBody) {
    if (normalizedPrefixes.length === 0) {
      return true;
    }

    if (!commentBody || typeof commentBody !== 'string') {
      core.info('Skipping 👀 reaction: no comment body to inspect.');
      return false;
    }

    const normalizedBody = commentBody.trimStart().toLowerCase();
    const matchesPrefix = normalizedPrefixes.some((prefix) =>
      normalizedBody.startsWith(prefix),
    );

    if (!matchesPrefix) {
      core.info('Skipping 👀 reaction: comment does not match required prefixes.');
    }

    return matchesPrefix;
  }

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
      if (!shouldReactToComment(payload.comment?.body)) {
        return;
      }
      await addCommentReaction(payload.comment?.id, 'issue');
    } else if (eventName === 'pull_request_review_comment') {
      if (!shouldReactToComment(payload.comment?.body)) {
        return;
      }
      await addCommentReaction(payload.comment?.id, 'review');
    } else {
      core.warning(`Unsupported event "${eventName}" for reaction step.`);
    }
  } catch (error) {
    core.warning(`Failed to add 👀 reaction: ${error.message}`);
  }
};
