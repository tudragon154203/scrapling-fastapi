import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import esmock from 'esmock';

const modulePath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../scripts/bots/gemini/prepare_prompt.js',
);

function buildOctokitMock({ files, commits, prData }) {
  const listFiles = () => {};
  const listCommits = () => {};
  return {
    rest: {
      pulls: {
        get: async () => ({ data: prData }),
        listFiles,
        listCommits,
      },
    },
    paginate: async (fn) => {
      if (fn === listFiles) {
        return files;
      }
      if (fn === listCommits) {
        return commits;
      }
      throw new Error('Unexpected paginate target');
    },
  };
}

test('prepare_prompt builds a rich prompt from GitHub context', async () => {
  const setOutputs = [];
  const warnings = [];
  const failures = [];

  const files = [
    {
      filename: '.specify/src/example.js',
      status: 'modified',
      additions: 10,
      deletions: 2,
      patch: 'diff --git a/.specify/src/example.js b/.specify/src/example.js\n@@\n-' + 'a'.repeat(1600),
    },
    {
      filename: 'docs/readme.md',
      status: 'added',
      additions: 5,
      deletions: 0,
      patch: null,
    },
  ];
  const commits = [
    {
      sha: 'abcdef1234567890',
      commit: { message: 'feat: add feature\n\nBody details' },
    },
  ];
  const prData = {
    number: 99,
    title: 'Improve feature',
    body: 'PR description',
    user: { login: 'octocat' },
    html_url: 'https://example.com/pr/99',
  };

  process.env.GITHUB_TOKEN = 'token';
  process.env.EVENT_NAME = 'pull_request';
  process.env.EVENT_PAYLOAD = JSON.stringify({
    pull_request: {
      number: 99,
      title: 'Improve feature',
      body: 'PR description',
      user: { login: 'octocat' },
      html_url: 'https://example.com/pr/99',
    },
    comment: {
      body: 'Please add more tests',
      html_url: 'https://example.com/pr/99#comment',
    },
  });
  process.env.GITHUB_REPOSITORY = 'octo/scrapling';

  const githubClient = buildOctokitMock({ files, commits, prData });

  try {
    await esmock(modulePath, {
      '@actions/core': {
        default: {
          setOutput: (name, value) => {
            setOutputs.push([name, value]);
          },
          setFailed: (message) => {
            failures.push(message);
          },
          warning: (message) => {
            warnings.push(message);
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
    delete process.env.EVENT_NAME;
    delete process.env.EVENT_PAYLOAD;
    delete process.env.GITHUB_REPOSITORY;
  }

  assert.deepEqual(warnings, [], 'no warnings should be emitted');
  assert.deepEqual(failures, [], 'prepare_prompt should not fail');

  const outputs = Object.fromEntries(setOutputs);
  assert.ok(outputs.prompt, 'prompt output should be set');
  assert.ok(
    outputs.prompt.includes('- .specify/src/example.js (modified, +10 / -2)'),
    'prompt should include formatted file details',
  );
  assert.ok(
    outputs.prompt.includes('```diff'),
    'prompt should include diff fenced block for patches',
  );
  assert.ok(
    outputs.prompt.includes('... (patch truncated)'),
    'prompt should mention truncated patches',
  );
  assert.ok(
    outputs.prompt.includes('- abcdef1'),
    'prompt should include abbreviated commit shas',
  );
  assert.ok(
    outputs.prompt.includes('Additional request from comment:'),
    'prompt should echo additional comment requests when present',
  );
  assert.equal(outputs.issue_number, '99');
  assert.equal(outputs.issue_title, 'Improve feature');
  assert.equal(outputs.issue_body, 'PR description');
  assert.equal(outputs.comment_body, 'Please add more tests');
});
