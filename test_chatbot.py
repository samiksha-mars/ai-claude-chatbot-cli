"""Tests use a fake client, so they run without an API key or the anthropic package."""

import io
import sys
import types
import unittest
from contextlib import redirect_stderr
from unittest import mock

from chat_session import MODEL, REFUSAL_MESSAGE, ChatSession
from chatbot import handle_api_error, has_credentials, main, run


def text_block(text):
    return types.SimpleNamespace(type="text", text=text)


class FakeStream:
    def __init__(self, chunks, stop_reason):
        self.text_stream = iter(chunks)
        self.final = types.SimpleNamespace(
            stop_reason=stop_reason, content=[text_block("".join(chunks))])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.final


class FakeMessages:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def stream(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        chunks, stop_reason = reply
        return FakeStream(chunks, stop_reason)


class FakeClient:
    def __init__(self, *replies):
        self.messages = FakeMessages(replies)


class FakeAPIError(Exception):
    pass


fake_anthropic = types.SimpleNamespace(
    AuthenticationError=type("AuthenticationError", (FakeAPIError,), {}),
    RateLimitError=type("RateLimitError", (FakeAPIError,), {}),
    APIStatusError=type("APIStatusError", (FakeAPIError,), {}),
    APIConnectionError=type("APIConnectionError", (FakeAPIError,), {}),
)


class ChatSessionTest(unittest.TestCase):

    def test_streams_and_returns_reply(self):
        client = FakeClient((["Hel", "lo!"], "end_turn"))
        session = ChatSession(client)
        streamed = []
        self.assertEqual(session.send("Hi", on_text=streamed.append), "Hello!")
        self.assertEqual(streamed, ["Hel", "lo!"])

    def test_sends_model_system_and_history(self):
        client = FakeClient((["A"], "end_turn"), (["B"], "end_turn"))
        session = ChatSession(client, system="Be brief.")
        session.send("first")
        session.send("second")
        call = client.messages.calls[1]
        self.assertEqual(call["model"], MODEL)
        self.assertEqual(call["system"], "Be brief.")
        self.assertEqual([m["role"] for m in call["messages"]], ["user", "assistant", "user"])
        self.assertNotIn("temperature", call)

    def test_reset_clears_history(self):
        session = ChatSession(FakeClient((["A"], "end_turn")))
        session.send("hi")
        session.reset()
        self.assertEqual(session.messages, [])

    def test_refusal_is_not_added_to_history(self):
        session = ChatSession(FakeClient(([], "refusal")))
        self.assertEqual(session.send("bad request"), REFUSAL_MESSAGE)
        self.assertEqual(session.messages, [])

    def test_error_rolls_back_user_message(self):
        session = ChatSession(FakeClient(RuntimeError("boom")))
        with self.assertRaises(RuntimeError):
            session.send("hi")
        self.assertEqual(session.messages, [])

    def test_interrupt_rolls_back_user_message(self):
        session = ChatSession(FakeClient(KeyboardInterrupt()))
        with self.assertRaises(KeyboardInterrupt):
            session.send("hi")
        self.assertEqual(session.messages, [])


class RunLoopTest(unittest.TestCase):

    def run_with_inputs(self, session, inputs):
        output = []
        feed = iter(inputs)

        def fake_input(prompt):
            try:
                return next(feed)
            except StopIteration:
                raise EOFError

        run(session, fake_anthropic, input_fn=fake_input, write=output.append)
        return "".join(output)

    def test_conversation_and_quit(self):
        session = ChatSession(FakeClient((["Hi there"], "end_turn")))
        output = self.run_with_inputs(session, ["hello", "/quit"])
        self.assertIn("claude> Hi there", output)
        self.assertTrue(output.endswith("Bye!\n"))

    def test_reset_command(self):
        session = ChatSession(FakeClient((["A"], "end_turn")))
        output = self.run_with_inputs(session, ["hi", "/reset"])
        self.assertIn("Conversation cleared.", output)
        self.assertEqual(session.messages, [])

    def test_api_error_is_reported_and_loop_continues(self):
        session = ChatSession(FakeClient(fake_anthropic.RateLimitError(), (["ok"], "end_turn")))
        output = self.run_with_inputs(session, ["one", "two"])
        self.assertIn("Rate limited", output)
        self.assertIn("ok", output)

    def test_ctrl_c_during_reply_keeps_chatting(self):
        session = ChatSession(FakeClient(KeyboardInterrupt(), (["still here"], "end_turn")))
        output = self.run_with_inputs(session, ["one", "two"])
        self.assertIn("[Reply interrupted.]", output)
        self.assertIn("claude> still here", output)
        self.assertEqual([m["content"] for m in session.messages if m["role"] == "user"], ["two"])


class HandleApiErrorTest(unittest.TestCase):

    def test_unknown_errors_are_not_handled(self):
        self.assertIsNone(handle_api_error(ValueError(), fake_anthropic))

    def test_authentication_error(self):
        message = handle_api_error(fake_anthropic.AuthenticationError(), fake_anthropic)
        self.assertIn("ANTHROPIC_API_KEY", message)


class CredentialsTest(unittest.TestCase):

    def test_has_credentials(self):
        self.assertTrue(has_credentials(types.SimpleNamespace(api_key="sk-test")))
        self.assertTrue(has_credentials(types.SimpleNamespace(api_key=None, credentials=object())))
        self.assertFalse(has_credentials(types.SimpleNamespace(api_key=None, auth_token=None)))

    def test_missing_credentials_exit_before_chatting(self):
        client = FakeClient()
        client.api_key = client.auth_token = client.credentials = None
        anthropic = types.SimpleNamespace(Anthropic=lambda: client)
        stderr = io.StringIO()
        with mock.patch.dict(sys.modules, anthropic=anthropic), redirect_stderr(stderr):
            self.assertEqual(main([]), 1)
        self.assertIn("ANTHROPIC_API_KEY", stderr.getvalue())
        self.assertEqual(client.messages.calls, [])


if __name__ == "__main__":
    unittest.main()
