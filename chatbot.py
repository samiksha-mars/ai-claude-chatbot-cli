"""Terminal chatbot powered by Claude."""

import argparse
import sys

from chat_session import DEFAULT_SYSTEM, REFUSAL_MESSAGE, ChatSession

BANNER = "Chatting with Claude. Commands: /reset (new conversation), /quit (exit)."


def handle_api_error(error, anthropic):
    """Turn SDK exceptions into a short, friendly message."""
    if isinstance(error, anthropic.AuthenticationError):
        return "Authentication failed. Set a valid ANTHROPIC_API_KEY and try again."
    if isinstance(error, anthropic.RateLimitError):
        return "Rate limited by the API. Wait a moment and try again."
    if isinstance(error, anthropic.APIStatusError):
        return f"API error ({error.status_code}): {error.message}"
    if isinstance(error, anthropic.APIConnectionError):
        return "Could not reach the API. Check your internet connection."
    return None


def run(session, anthropic, input_fn=input, write=sys.stdout.write):
    write(BANNER + "\n")
    while True:
        try:
            user_text = input_fn("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            write("\nBye!\n")
            return
        if not user_text:
            continue
        if user_text in ("/quit", "/exit"):
            write("Bye!\n")
            return
        if user_text == "/reset":
            session.reset()
            write("Conversation cleared.\n")
            continue

        write("claude> ")
        try:
            reply = session.send(user_text, on_text=write)
        except Exception as error:  # noqa: BLE001 - mapped to friendly messages below
            message = handle_api_error(error, anthropic)
            if message is None:
                raise
            write(f"\n[{message}]\n")
            continue
        if reply == REFUSAL_MESSAGE:
            write(reply)
        write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Chat with Claude in your terminal.")
    parser.add_argument("--system", default=DEFAULT_SYSTEM, help="system prompt for the assistant")
    args = parser.parse_args(argv)

    try:
        import anthropic
    except ImportError:
        print("The anthropic package is missing. Run: pip install -r requirements.txt",
              file=sys.stderr)
        return 1

    session = ChatSession(anthropic.Anthropic(), system=args.system)
    run(session, anthropic)
    return 0


if __name__ == "__main__":
    sys.exit(main())
