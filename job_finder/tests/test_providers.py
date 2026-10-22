"""Tests for each provider's own job: sending a request and turning the
service's reply into (answer, usage). The service is replaced by a recorded
reply, so neither Claude Code nor Ollama is started."""

import json
import subprocess

import httpx
import pytest

from providers import ProviderError
from providers import claude_code, ollama


# ---- Claude Code -------------------------------------------------------------------

def run_claude_replying(monkeypatch, returncode=0, stdout="", stderr=""):
    """Make 'running Claude Code' return a recorded reply. Returns what was run."""
    calls = []
    monkeypatch.setattr(claude_code, "find_claude", lambda: "claude")

    def fake_run(command, **options):
        calls.append({"command": command, **options})
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)
    monkeypatch.setattr(claude_code.subprocess, "run", fake_run)
    return calls


def test_claude_code_reply_is_read(monkeypatch):
    reply = {"is_error": False, "structured_output": {"professional_years": 1},
             "total_cost_usd": 0.10834,
             "usage": {"input_tokens": 2, "cache_creation_input_tokens": 6235,
                       "cache_read_input_tokens": 4086, "output_tokens": 2843},
             "modelUsage": {"claude-haiku-5-5": {"outputTokens": 30},
                            "claude-opus-5-5": {"outputTokens": 2813}}}
    calls = run_claude_replying(monkeypatch, stdout=json.dumps(reply))

    answer, usage = claude_code.ClaudeCode().ask("instructions", "the CV", {"type": "object"})

    assert answer == {"professional_years": 1}
    assert usage["model"] == "claude-opus-5-5"          # the one that wrote the most
    assert usage["cache_write_tokens"] == 6235 and usage["cost_equivalent_usd"] == 0.1083
    # Safety: no tools, nothing saved, the prompt through standard input.
    command = calls[0]["command"]
    assert command[command.index("--tools") + 1] == ""
    assert "--no-session-persistence" in command
    assert calls[0]["input"] == "the CV" and "the CV" not in command


def test_claude_code_missing_is_explained(monkeypatch):
    monkeypatch.setattr(claude_code, "find_claude", lambda: None)
    with pytest.raises(ProviderError, match="isn't installed"):
        claude_code.ClaudeCode().ask("", "", {})


def test_claude_code_error_is_explained(monkeypatch):
    run_claude_replying(monkeypatch, returncode=1, stderr="You've hit your usage limit")
    with pytest.raises(ProviderError, match="usage limit"):
        claude_code.ClaudeCode().ask("", "", {})


# ---- Ollama ------------------------------------------------------------------------

def test_ollama_lists_installed_models(monkeypatch):
    def fake_get(url, timeout):
        return httpx.Response(200, request=httpx.Request("GET", url),
                              json={"models": [{"name": "llama3.1:8b"}, {"name": "gemma3:270m"}]})
    monkeypatch.setattr(ollama.httpx, "get", fake_get)
    assert ollama.Ollama().list_models() == ["gemma3:270m", "llama3.1:8b"]


def test_ollama_reply_is_read(monkeypatch):
    sent = []

    def fake_post(url, json, timeout):
        sent.append(json)
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "message": {"content": '{"professional_years": 1}'},
            "prompt_eval_count": 900, "eval_count": 40})
    monkeypatch.setattr(ollama.httpx, "post", fake_post)

    answer, usage = ollama.Ollama("llama3.1:8b").ask("instructions", "the CV", {"type": "object"})

    assert answer == '{"professional_years": 1}'      # JSON text; scoring.py reads it
    assert usage["input_tokens"] == 900 and usage["output_tokens"] == 40
    assert sent[0]["format"] == {"type": "object"}    # the answer shape is enforced
    assert sent[0]["options"]["temperature"] == 0


def test_ollama_not_running_is_explained(monkeypatch):
    def refuse(url, json, timeout):
        raise httpx.ConnectError("connection refused")
    monkeypatch.setattr(ollama.httpx, "post", refuse)
    with pytest.raises(ProviderError, match="Ollama is not running"):
        ollama.Ollama().ask("", "", {})


# ---- OpenAI-compatible APIs ----------------------------------------------------------

from providers import openai_compatible  # noqa: E402

KEY = "gsk_secret_test_key_123"


def api_replying(monkeypatch, *replies):
    """Make the service answer with the given (status, body) pairs, in order.
    Returns the requests sent."""
    sent = []

    def fake_request(method, url, headers, json, timeout):
        sent.append({"method": method, "url": url, "headers": headers, "json": json})
        status, body = replies[len(sent) - 1]
        return httpx.Response(status, request=httpx.Request(method, url),
                              **({"json": body} if isinstance(body, dict) else {"text": body}))
    monkeypatch.setattr(openai_compatible.httpx, "request", fake_request)
    return sent


def groq(model="some-model", api_key=KEY):
    return openai_compatible.OpenAICompatible("Groq", "https://api.groq.com/openai/v1",
                                              model, api_key)


OK_REPLY = {"model": "some-model-2026",
            "choices": [{"message": {"content": '{"professional_years": 1}'}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 30,
                      "prompt_tokens_details": {"cached_tokens": 200}}}


def test_api_request_and_reply(monkeypatch):
    sent = api_replying(monkeypatch, (200, OK_REPLY))
    provider = groq()

    answer, usage = provider.ask("instructions", "the CV", {"type": "object"})

    assert sent[0]["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert sent[0]["headers"] == {"Authorization": f"Bearer {KEY}"}
    assert sent[0]["json"]["response_format"]["type"] == "json_schema"
    assert answer == '{"professional_years": 1}'
    assert usage["input_tokens"] == 1000 and usage["cache_read_tokens"] == 200
    assert provider.reviewer_prefix == "Groq" and provider.label == "some-model through Groq"


def test_api_falls_back_to_plain_json_when_the_schema_is_refused(monkeypatch):
    sent = api_replying(monkeypatch, (400, "response_format json_schema not supported"),
                        (200, OK_REPLY))
    answer, _ = groq().ask("instructions", "the CV", {"type": "object", "title": "Facts"})
    assert sent[1]["json"]["response_format"] == {"type": "json_object"}
    assert '"title": "Facts"' in sent[1]["json"]["messages"][0]["content"]  # schema in the instructions
    assert answer == '{"professional_years": 1}'


@pytest.mark.parametrize("status, message", [
    (401, "refused the API key"),
    (404, "doesn't know the model"),
    (429, "limit was reached"),
    (500, "error 500"),
])
def test_api_errors_are_plain_and_never_show_the_key(monkeypatch, status, message):
    api_replying(monkeypatch, (status, "something went wrong"))
    with pytest.raises(ProviderError, match=message) as raised:
        groq().ask("", "", {})
    assert KEY not in str(raised.value)


def test_api_without_a_model_says_what_to_do():
    with pytest.raises(ProviderError, match="Choose a model for Groq"):
        groq(model="").ask("", "", {})


def test_api_lists_its_models(monkeypatch):
    sent = api_replying(monkeypatch, (200, {"data": [{"id": "model-b"}, {"id": "model-a"}]}))
    assert groq().list_models() == ["model-a", "model-b"]
    assert sent[0]["method"] == "GET" and sent[0]["url"].endswith("/v1/models")
    assert sent[0]["headers"] == {"Authorization": f"Bearer {KEY}"}


def test_a_local_service_needs_no_key(monkeypatch):
    sent = api_replying(monkeypatch, (200, OK_REPLY))
    openai_compatible.OpenAICompatible("LM Studio", "http://localhost:1234/v1", "local-model",
                                       api_key="").ask("", "", {})
    assert sent[0]["url"].startswith("http://localhost:1234/v1")
    assert sent[0]["headers"] == {}   # no key is sent at all


def test_claude_code_runs_without_a_console_window(monkeypatch):
    calls = run_claude_replying(monkeypatch, stdout=json.dumps(
        {"is_error": False, "structured_output": {}, "usage": {}, "modelUsage": {}}))
    claude_code.ClaudeCode().ask("", "", {})
    assert calls[0]["creationflags"] == claude_code.NO_WINDOW


# ---- Claude through the Anthropic API ----------------------------------------------------

from providers import anthropic_api  # noqa: E402

ANTHROPIC_KEY = "sk-ant-secret-test-key-0000"


def anthropic_replying(monkeypatch, status, body):
    sent = []

    def fake_request(method, url, headers, json, timeout):
        sent.append({"method": method, "url": url, "headers": headers, "json": json})
        return httpx.Response(status, request=httpx.Request(method, url), json=body)
    monkeypatch.setattr(anthropic_api.httpx, "request", fake_request)
    return sent


def test_claude_api_request_and_reply(monkeypatch):
    sent = anthropic_replying(monkeypatch, 200, {
        "model": "claude-test-1",
        "content": [{"type": "text", "text": "Here it is."},
                    {"type": "tool_use", "name": "answer", "input": {"professional_years": 1}}],
        "usage": {"input_tokens": 900, "output_tokens": 40, "cache_creation_input_tokens": 1500,
                  "cache_read_input_tokens": 0}})

    answer, usage = anthropic_api.AnthropicAPI("claude-test-1", ANTHROPIC_KEY).ask(
        "instructions", "the CV", {"type": "object"})

    request = sent[0]
    assert request["url"] == "https://api.anthropic.com/v1/messages"
    assert request["headers"]["x-api-key"] == ANTHROPIC_KEY
    # The answer must come through the "answer" tool, whose input is our schema.
    assert request["json"]["tool_choice"] == {"type": "tool", "name": "answer"}
    assert request["json"]["tools"][0]["input_schema"] == {"type": "object"}
    # The instructions are cached between batches.
    assert request["json"]["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert answer == {"professional_years": 1}
    assert usage["cache_write_tokens"] == 1500 and usage["output_tokens"] == 40


@pytest.mark.parametrize("status, message", [
    (401, "refused the API key"), (404, "doesn't know the model"),
    (429, "rate limit"), (529, "overloaded"), (400, "credit balance is too low"),
])
def test_claude_api_errors_are_plain_and_never_show_the_key(monkeypatch, status, message):
    anthropic_replying(monkeypatch, status,
                       {"error": {"message": "Your credit balance is too low"}})
    with pytest.raises(ProviderError, match=message) as raised:
        anthropic_api.AnthropicAPI("claude-test-1", ANTHROPIC_KEY).ask("", "", {})
    assert ANTHROPIC_KEY not in str(raised.value)


def test_claude_api_lists_models_newest_first(monkeypatch):
    anthropic_replying(monkeypatch, 200, {"data": [{"id": "claude-a-1"}, {"id": "claude-b-2"}]})
    assert anthropic_api.AnthropicAPI("", ANTHROPIC_KEY).list_models() == ["claude-b-2", "claude-a-1"]


def test_claude_api_needs_a_key_and_a_model():
    with pytest.raises(ProviderError, match="API key"):
        anthropic_api.AnthropicAPI("claude-test-1", "").ask("", "", {})
    with pytest.raises(ProviderError, match="Choose a Claude model"):
        anthropic_api.AnthropicAPI("", ANTHROPIC_KEY).ask("", "", {})
