import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import esmock from 'esmock';

const modulePath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../scripts/bots/gemini/post_response.js',
);

async function runPostResponseWithMocks({
  payload,
  summary,
  error,
  status = 'success',
}) {
  const infoMessages = [];
  const failures = [];
  const comments = [];

  process.env.GITHUB_TOKEN = 'token';
  process.env.EVENT_PAYLOAD = JSON.stringify(payload);
  process.env.GITHUB_REPOSITORY = 'octo/scrapling';
  process.env.GEMINI_STATUS = status;
  if (summary !== undefined) {
    process.env.GEMINI_SUMMARY = summary;
  } else {
    delete process.env.GEMINI_SUMMARY;
  }
  if (error !== undefined) {
    process.env.GEMINI_ERROR = error;
  } else {
    delete process.env.GEMINI_ERROR;
  }

  const githubClient = {
    rest: {
      issues: {
        createComment: async (options) => {
          comments.push(options);
        },
      },
    },
  };

  try {
    await esmock(modulePath, {
      '@actions/core': {
        default: {
          info: (message) => {
            infoMessages.push(message);
          },
          setFailed: (message) => {
            failures.push(message);
          },
        },
      },
      '@actions/github': {
        context: { repo: { owner: 'octo', repo: 'scrapling' } },
        getOctokit: () => githubClient,
      },
    });
  } finally {
    delete process.env.GITHUB_TOKEN;
    delete process.env.EVENT_PAYLOAD;
    delete process.env.GITHUB_REPOSITORY;
    delete process.env.GEMINI_STATUS;
    delete process.env.GEMINI_SUMMARY;
    delete process.env.GEMINI_ERROR;
  }

  return { infoMessages, failures, comments };
}

test('post_response posts combined Gemini output', async () => {
  const { infoMessages, failures, comments } = await runPostResponseWithMocks({
    payload: { issue: { number: 7 } },
    summary: 'Summary text',
    error: 'Stack trace',
    status: 'failure',
  });

  assert.deepEqual(infoMessages, [], 'no info message should be logged on success');
  assert.deepEqual(failures, [], 'run should succeed');
  assert.equal(comments.length, 1, 'a comment should be created');
  const [comment] = comments;
  assert.equal(comment.owner, 'octo');
  assert.equal(comment.repo, 'scrapling');
  assert.equal(comment.issue_number, 7);
  assert.equal(typeof comment.body, 'string', 'body should be a string');
  assert.ok(comment.body.includes('## Gemini Review'), 'body should include review section');
  assert.ok(comment.body.includes('Summary text'), 'body should include summary');
  assert.ok(comment.body.includes('## Gemini Error'), 'body should include error section');
  assert.ok(comment.body.includes('Stack trace'), 'body should include error details');
  assert.ok(
    comment.body.includes('Gemini CLI step ended with status: **failure**.'),
    'body should mention non-success status',
  );
});

test('post_response skips when issue number is unavailable', async () => {
  const { infoMessages, comments, failures } = await runPostResponseWithMocks({
    payload: {},
  });

  assert.deepEqual(comments, [], 'no comment should be created');
  assert.deepEqual(failures, [], 'run should not fail when skipping');
  assert.deepEqual(infoMessages, ['No issue or pull request number found; skipping comment.']);
});

test('post_response reports failures from GitHub API', async () => {
  const failingClient = {
    rest: {
      issues: {
        createComment: async () => {
          throw new Error('network error');
        },
      },
    },
  };

  const infoMessages = [];
  const failures = [];

  process.env.GITHUB_TOKEN = 'token';
  process.env.EVENT_PAYLOAD = JSON.stringify({ pull_request: { number: 3 } });
  process.env.GITHUB_REPOSITORY = 'octo/scrapling';
  process.env.GEMINI_SUMMARY = 'Summary';

  try {
    await esmock(modulePath, {
      '@actions/core': {
        default: {
          info: (message) => {
            infoMessages.push(message);
          },
          setFailed: (message) => {
            failures.push(message);
          },
        },
      },
      '@actions/github': {
        context: { repo: { owner: 'octo', repo: 'scrapling' } },
        getOctokit: () => failingClient,
      },
    });
  } finally {
    delete process.env.GITHUB_TOKEN;
    delete process.env.EVENT_PAYLOAD;
    delete process.env.GITHUB_REPOSITORY;
    delete process.env.GEMINI_SUMMARY;
  }

  assert.deepEqual(infoMessages, [], 'no info messages expected on failure');
  assert.equal(failures.length, 1, 'setFailed should be called once');
  assert.match(failures[0], /post_response failed: network error/);
});
