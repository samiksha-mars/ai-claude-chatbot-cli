# AI Claude Chatbot CLI

A small multi-turn chatbot for the terminal powered by Claude, using the official
[Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python).

## Features

- Multi-turn conversation: Claude remembers what you said earlier in the session
- Streams replies token by token as they are generated
- Custom system prompt with `--system`
- `/reset` to start a new conversation, `/quit` to exit
- Friendly error messages for missing keys, rate limits and network issues

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-api-key
```

## Usage

```bash
python3 chatbot.py
```

```
Chatting with Claude. Commands: /reset (new conversation), /quit (exit).

you> My name is Sam. Give me one tip for learning Python.
claude> Nice to meet you, Sam! Write a small project you actually care about ...

you> What's my name?
claude> Your name is Sam.
```

Give the assistant a different personality with a system prompt:

```bash
python3 chatbot.py --system "You are a pirate. Answer every question like a pirate."
```

## Configuration

The model and limits live at the top of `chat_session.py`:

| Setting      | Default           |
|--------------|-------------------|
| `MODEL`      | `claude-opus-5-5` |
| `MAX_TOKENS` | `16000`           |
| effort       | `low` (fast, inexpensive replies for chat) |

## Tests

The tests use a fake client, so they need neither an API key nor network access:

```bash
python3 -m unittest test_chatbot.py
```
