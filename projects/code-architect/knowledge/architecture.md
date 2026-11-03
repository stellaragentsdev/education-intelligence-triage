# Project Architecture Overview

## Tech Stack
- Frontend: Single-page WebApp with Vanilla CSS, Marked.js, Highlight.js
- Backend: Python `ThreadingHTTPServer` local proxy (`server.py`)
- LLM Provider: Local Ollama server (`http://127.0.0.1:11434`)
- Persistence: JSON file storage (`chats.json`, `projects/`)
