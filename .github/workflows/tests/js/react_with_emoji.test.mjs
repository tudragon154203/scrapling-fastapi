import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const modulePath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../scripts/bots/common/javascript/react_with_emoji.cjs',
);
const reactWithEmoji = require(modulePath);

function withEventEnv(name, payload, fn) {
  process.env.EVENT_NAME = name;
  if (payload !== undefined) {
    process.env.EVENT_PAYLOAD = payload;
  } else {
    delete process.env.EVENT_PAYLOAD;
  }

  return fn().finally(() => {
    delete process.env.EVENT_NAME;
    delete process.env.EVENT_PAYLOAD;
  });
}

test('adds issue reactions for pull request events', async () => {
  const reactions = [];
  const warnings = [];
  const github = {
    rest: {
      reactions: {
        createForIssue: async (options) => {
          reactions.push(options);
        },
      },
    },
  };
  const core = { warning: (message) => warnings.push(message) };
  const context = { repo: { owner: 'octo', repo: 'scrapling' } };

  await withEventEnv(
    'pull_request',
    JSON.stringify({ pull_request: { number: 7 } }),
    () => reactWithEmoji({ github, context, core, reaction: ' rocket ' }),
  );

  assert.deepEqual(reactions, [
    { owner: 'octo', repo: 'scrapling', issue_number: 7, content: 'rocket' },
  ]);
  assert.deepEqual(warnings, []);
});

test('adds review comment reactions for pull request review comments', async () => {
  const reviewReactions = [];
  const github = {
    rest: {
      reactions: {
        createForPullRequestReviewComment: async (options) => {
          reviewReactions.push(options);
        },
      },
    },
  };
  const warnings = [];
  const core = { warning: (message) => warnings.push(message) };
  const context = { repo: { owner: 'octo', repo: 'scrapling' } };

  await withEventEnv(
    'pull_request_review_comment',
    JSON.stringify({ comment: { id: 123 } }),
    () => reactWithEmoji({ github, context, core, reaction: 'eyes' }),
  );

  assert.deepEqual(reviewReactions, [
    { owner: 'octo', repo: 'scrapling', comment_id: 123, content: 'eyes' },
  ]);
  assert.deepEqual(warnings, []);
});

test('warns and skips when comment identifiers are missing', async () => {
  const github = {
    rest: {
      reactions: {
        createForIssueComment: async () => {
          throw new Error('should not be called');
        },
      },
    },
  };
  const warnings = [];
  const core = { warning: (message) => warnings.push(message) };
  const context = { repo: { owner: 'octo', repo: 'scrapling' } };

  await withEventEnv(
    'issue_comment',
    JSON.stringify({ comment: {} }),
    () => reactWithEmoji({ github, context, core, reaction: '   ' }),
  );

  assert.deepEqual(warnings, ['No issue comment id found for reaction.']);
});

test('warns when event payload cannot be parsed', async () => {
  const warnings = [];
  const github = {
    rest: {
      reactions: {
        createForIssue: async () => {
          throw new Error('should not be called');
        },
      },
    },
  };
  const core = { warning: (message) => warnings.push(message) };
  const context = { repo: { owner: 'octo', repo: 'scrapling' } };

  await withEventEnv(
    'pull_request',
    '{invalid-json',
    () => reactWithEmoji({ github, context, core, reaction: 'eyes' }),
  );

  assert.equal(warnings.length, 2);
  assert.match(warnings[0], /Failed to parse EVENT_PAYLOAD/);
  assert.equal(warnings[1], 'No issue or PR number found for reaction.');
});

test('reports GitHub API failures and includes emoji name in warning', async () => {
  const warnings = [];
  const github = {
    rest: {
      reactions: {
        createForIssue: async () => {
          throw new Error('boom');
        },
      },
    },
  };
  const core = { warning: (message) => warnings.push(message) };
  const context = { repo: { owner: 'octo', repo: 'scrapling' } };

  await withEventEnv(
    'issues',
    JSON.stringify({ issue: { number: 99 } }),
    () => reactWithEmoji({ github, context, core, reaction: 'thumbs_up' }),
  );

  assert.equal(warnings.length, 1);
  assert.equal(warnings[0], 'Failed to add thumbs_up reaction: boom');
});

test('warns when event type is unsupported', async () => {
  const warnings = [];
  const github = { rest: { reactions: {} } };
  const core = { warning: (message) => warnings.push(message) };
  const context = { repo: { owner: 'octo', repo: 'scrapling' } };

  await withEventEnv(
    'schedule',
    JSON.stringify({}),
    () => reactWithEmoji({ github, context, core, reaction: 'eyes' }),
  );

  assert.deepEqual(warnings, ['Unsupported event "schedule" for reaction step.']);
});
