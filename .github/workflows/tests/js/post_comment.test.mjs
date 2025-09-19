import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const postCommentModulePath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../scripts/bots/common/javascript/post_comment.js',
);
const { postComment } = require(postCommentModulePath);

test('postComment skips when body is empty', async () => {
  let called = false;
  const github = {
    rest: {
      issues: {
        createComment: async () => {
          called = true;
        },
      },
    },
  };

  await postComment(github, { repo: { owner: 'octo', repo: 'repo' } }, '   ', 123);
  assert.equal(called, false, 'createComment should not be called for empty body');
});

test('postComment skips when issue number is missing', async () => {
  let called = false;
  const github = {
    rest: {
      issues: {
        createComment: async () => {
          called = true;
        },
      },
    },
  };

  await postComment(github, { repo: { owner: 'octo', repo: 'repo' } }, 'A body', undefined);
  assert.equal(called, false, 'createComment should not be called without issue number');
});

test('postComment posts comment when inputs are valid', async () => {
  const calls = [];
  const github = {
    rest: {
      issues: {
        createComment: async (input) => {
          calls.push(input);
          return { data: { id: 1 } };
        },
      },
    },
  };
  const context = { repo: { owner: 'octo', repo: 'repo' } };

  await postComment(github, context, 'Hello world', 42);

  assert.equal(calls.length, 1, 'createComment should be called once');
  assert.deepEqual(calls[0], {
    owner: 'octo',
    repo: 'repo',
    issue_number: 42,
    body: 'Hello world',
  });
});

test('postComment rethrows errors from GitHub client', async () => {
  const github = {
    rest: {
      issues: {
        createComment: async () => {
          throw new Error('boom');
        },
      },
    },
  };
  const context = { repo: { owner: 'octo', repo: 'repo' } };

  await assert.rejects(
    () => postComment(github, context, 'Hello world', 42),
    /boom/,
  );
});
