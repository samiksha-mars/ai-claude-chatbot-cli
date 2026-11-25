"""Conversation state and streaming calls to the Claude Messages API."""

MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
DEFAULT_SYSTEM = "You are a friendly, concise assistant chatting in a terminal."
REFUSAL_MESSAGE = "[Claude declined to answer this message. Try rephrasing it.]"


class ChatSession:
    """Keeps the message history and sends it to Claude on every turn."""

    def __init__(self, client, system=DEFAULT_SYSTEM, model=MODEL):
        self.client = client
        self.system = system
        self.model = model
        self.messages = []

    def reset(self):
        self.messages = []

    def send(self, user_text, on_text=lambda text: None):
        """Send a user message, stream the reply through `on_text`, return the full reply."""
        self.messages.append({"role": "user", "content": user_text})
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=self.system,
                messages=self.messages,
                output_config={"effort": "low"},
            ) as stream:
                for text in stream.text_stream:
                    on_text(text)
                final = stream.get_final_message()
        except BaseException:  # includes KeyboardInterrupt (Ctrl+C mid-reply)
            # Drop the unanswered user turn so the history stays valid.
            self.messages.pop()
            raise

        if final.stop_reason == "refusal":
            self.messages.pop()
            return REFUSAL_MESSAGE

        self.messages.append({"role": "assistant", "content": final.content})
        return "".join(block.text for block in final.content if block.type == "text")
