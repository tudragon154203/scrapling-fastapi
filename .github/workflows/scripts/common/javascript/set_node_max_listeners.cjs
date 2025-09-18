const events = require('node:events');

const limit = 30;

try {
  // Increase the default listener ceiling for EventEmitters/EventTargets used by the Gemini CLI.
  events.setMaxListeners(limit);
} catch (error) {
  // Fallback for very old Node.js versions where setMaxListeners may not accept a single argument.
  if (typeof events.defaultMaxListeners === 'number') {
    events.defaultMaxListeners = limit;
  }
}

// Best-effort: ensure any AbortSignal instance created after this uses the higher limit as well.
try {
  if (typeof AbortController !== 'undefined') {
    const controller = new AbortController();
    events.setMaxListeners(limit, controller.signal);
  }
} catch (error) {
  // Ignore failures; increasing the global default already prevents warnings in practice.
}

if (process.env.ACTIONS_STEP_DEBUG === 'true') {
  console.debug(`Gemini workflow max listeners raised to ${limit}`);
}