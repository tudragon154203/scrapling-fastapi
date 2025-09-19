import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';

const require = createRequire(import.meta.url);
const modulePath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../scripts/bots/common/javascript/set_node_max_listeners.cjs',
);
const moduleSource = await readFile(modulePath, 'utf8');

function resetModuleCache() {
  const resolved = require.resolve(modulePath);
  delete require.cache[resolved];
}

test('raises EventEmitter defaults to the expected limit', async () => {
  const events = require('node:events');
  const originalDefault = events.defaultMaxListeners;

  resetModuleCache();
  try {
    events.setMaxListeners(originalDefault);
    require(modulePath);

    const emitter = new events.EventEmitter();
    assert.equal(emitter.getMaxListeners(), 30);
  } finally {
    resetModuleCache();
    events.setMaxListeners(originalDefault);
    if (typeof originalDefault === 'number') {
      events.defaultMaxListeners = originalDefault;
    }
  }
});

test('falls back to updating defaultMaxListeners when setMaxListeners throws', async () => {
  const calls = [];
  const eventsMock = {
    defaultMaxListeners: 1,
    setMaxListeners(limit, target) {
      calls.push([limit, target]);
      if (arguments.length === 1) {
        throw new TypeError('legacy runtime');
      }
      this.defaultMaxListeners = limit;
    },
  };

  const context = {
    require: (specifier) => {
      if (specifier === 'node:events') {
        return eventsMock;
      }
      throw new Error(`Unexpected require: ${specifier}`);
    },
    module: { exports: {} },
    exports: {},
    process: { env: {} },
    console: { debug: () => {} },
    AbortController: function MockAbortController() {
      this.signal = { type: 'mock-signal' };
    },
  };

  vm.runInNewContext(moduleSource, context, { filename: modulePath });

  assert.equal(eventsMock.defaultMaxListeners, 30);
  assert.equal(calls.length, 2);
  assert.equal(calls[0][0], 30);
  assert.equal(calls[1][0], 30);
  assert.equal(typeof calls[1][1], 'object');
  assert.ok(calls[1][1]);
});

test('logs debug output when ACTIONS_STEP_DEBUG is true', async () => {
  const events = require('node:events');
  const originalDefault = events.defaultMaxListeners;
  const originalDebug = console.debug;
  const messages = [];

  resetModuleCache();
  process.env.ACTIONS_STEP_DEBUG = 'true';
  console.debug = (message) => {
    messages.push(message);
  };

  try {
    require(modulePath);
    assert.deepEqual(messages, ['Gemini workflow max listeners raised to 30']);
  } finally {
    console.debug = originalDebug;
    delete process.env.ACTIONS_STEP_DEBUG;
    resetModuleCache();
    events.setMaxListeners(originalDefault);
    if (typeof originalDefault === 'number') {
      events.defaultMaxListeners = originalDefault;
    }
  }
});
