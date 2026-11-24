# AI Claude Chatbot CLI

A small multi-turn chatbot for the terminal powered by Claude, using the official
[Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python).

## Features

- Multi-turn conversation: Claude remembers what you said earlier in the session
- Streams replies token by token as they are generated
- Custom system prompt with `--system`
- `/reset` to start a new conversation, `/quit` to exit
- Friendly error messages for missing keys, rate limits and network issues
