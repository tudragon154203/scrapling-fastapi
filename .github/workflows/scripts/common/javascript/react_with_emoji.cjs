async function reactWithEmoji({ github, context, core, reaction }) {
  const eventName = process.env.EVENT_NAME;
  let payload = {};

  const emoji = typeof reaction === 'string' && reaction.trim().length > 0 ? reaction.trim() : 'eyes';

  try {
    payload = JSON.parse(process.env.EVENT_PAYLOAD || '{}');
  } catch (error) {
    core.warning(`Failed to parse EVENT_PAYLOAD: ${error.message}`);
  }

  const { repo } = context;
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
      content: emoji,
    });
  }

  async function addCommentReaction(commentId, type) {
    if (!commentId) {
      core.warning(`No ${type} comment id found for reaction.`);
      return;
    }

    const params = { owner, repo: repository, comment_id: commentId, content: emoji };
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
    } else if (eventName === 'issues') {
      await addIssueReaction(payload.issue?.number);
    } else {
      core.warning(`Unsupported event "${eventName}" for reaction step.`);
    }
  } catch (error) {
    core.warning(`Failed to add ${emoji} reaction: ${error.message}`);
  }
}

module.exports = reactWithEmoji;