#!/bin/bash
set -euo pipefail

mkdir -p ~/.claude-code-router
cat > ~/.claude-code-router/config.json <<EOF
{
  "LOG": false,
  "LOG_LEVEL": "info",
  "CLAUDE_PATH": "",
  "HOST": "127.0.0.1",
  "PORT": 3456,
  "APIKEY": "",
  "API_TIMEOUT_MS": "60000",
  "PROXY_URL": "",
  "transformers": [],
  "Providers": [
    {
      "name": "openrouter",
      "api_base_url": "https://openrouter.ai/api/v1/chat/completions",
      "api_key": "${OPENROUTER_API_KEY}",
      "models": [
        "qwen/qwen3-coder:free",
        "z-ai/glm-4.5-air:free",
        "moonshotai/kimi-k2:free",
        "deepseek/deepseek-chat-v3.1:free",
        "openrouter/sonoma-sky-alpha"
      ],
      "transformer": {
        "use": [
          "openrouter"
        ],
        "tngtech/deepseek-r1t2-chimera:free": {
          "use": [
            "deepseek"
          ]
        },
        "deepseek/deepseek-chat-v3-0324:free": {
          "use": [
            "deepseek"
          ]
        }
      }
    },
    {
      "name": "gemini",
      "api_base_url": "https://generativelanguage.googleapis.com/v1beta/models/",
      "api_key": "${GEMINI_API_KEY}",
      "models": [
        "${GEMINI_MODEL}"
      ],
      "transformer": {
        "use": [
          "gemini"
        ]
      }
    }
  ],
  "StatusLine": {
    "enabled": true,
    "currentStyle": "default",
    "default": {
      "modules": [
        {
          "type": "workDir",
          "icon": "",
          "text": "{{workDirName}}",
          "color": "bright_blue"
        },
        {
          "type": "model",
          "icon": "",
          "text": "{{model}}",
          "color": "bright_yellow"
        },
        {
          "type": "usage",
          "icon": "",
          "text": "{{inputTokens}} / {{outputTokens}}",
          "color": "bright_magenta"
        },
        {
          "type": "script",
          "icon": "",
          "text": "Script Module",
          "color": "bright_cyan",
          "scriptPath": ""
        }
      ]
    },
    "powerline": {
      "modules": []
    }
  },
  "Router": {
    "default": "openrouter,${OPENROUTER_MODEL}",
    "background": "openrouter,moonshotai/kimi-k2:free",
    "think": "openrouter,deepseek/deepseek-chat-v3.1:free",
    "longContext": "gemini,${GEMINI_MODEL}",
    "longContextThreshold": 100000,
    "webSearch": "openrouter,moonshotai/kimi-k2:free"
  }
}
EOF
nohup ~/.bun/bin/bunx @musistudio/claude-code-router@latest start &
# Temporary fixed delay until healthcheck is reintroduced
sleep 5