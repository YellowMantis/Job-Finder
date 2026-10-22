"""Claude through the Anthropic API, with your own API key (console.anthropic.com).

This is separate from a Claude plan (Pro, Max): a plan is used through Claude
Code (claude_code.py); an API key is paid per token. Through the API there is
no Claude Code program to start for every batch, and batches can run at the
same time, so scoring many jobs is quicker.

The answer's shape: the request offers one "tool" whose input is our JSON
schema and requires the model to use it, so the answer always comes back in
that shape. The instructions are marked for prompt caching: in a scoring run,
every batch after the first reuses them at a fraction of the price.

The key is sent only to api.anthropic.com, and never written to a log, a
message or a file.
"""

import time

import httpx

from providers.base import Provider, ProviderError
from settings import API_BATCH_SIZE

API_URL = "https://api.anthropic.com/v1"
API_VERSION = "2023-06-01"  # the version of the request format, not of the model
MAX_ANSWER_TOKENS = 16000   # room for a batch of detailed reviews


class AnthropicAPI(Provider):
    id = "anthropic"
    label = "Claude, through the Anthropic API"
    reviewer_prefix = "Claude API"
    batch_size = API_BATCH_SIZE
    requests_at_once = 3  # an API answers several requests at once; Claude Code is one program

    def __init__(self, model="", api_key=""):
        self.model = model
        self.api_key = api_key

    def list_models(self):
        reply = self._request("GET", "/models?limit=100")
        return sorted((model["id"] for model in reply.get("data", [])), reverse=True)

    def ask(self, system_prompt, prompt, schema):
        if not self.model:
            raise ProviderError("Choose a Claude model first.")
        started = time.monotonic()
        reply = self._request("POST", "/messages", {
            "model": self.model,
            "max_tokens": MAX_ANSWER_TOKENS,
            "temperature": 0,  # the same input gives the same answer
            "system": [{"type": "text", "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{"name": "answer", "description": "Give the answer in this exact shape.",
                       "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": "answer"},
        })
        answer = next((block["input"] for block in reply.get("content", [])
                       if block.get("type") == "tool_use"), None)
        if answer is None:
            raise ProviderError("Claude answered without using the answer format.")
        usage = reply.get("usage") or {}
        return answer, {
            "model": reply.get("model") or self.model,
            "input_tokens": usage.get("input_tokens") or 0,
            "cache_write_tokens": usage.get("cache_creation_input_tokens") or 0,
            "cache_read_tokens": usage.get("cache_read_input_tokens") or 0,
            "output_tokens": usage.get("output_tokens") or 0,
            "seconds": round(time.monotonic() - started),
        }

    def _request(self, method, path, body=None):
        if not self.api_key:
            raise ProviderError("Paste your Anthropic API key first.")
        headers = {"x-api-key": self.api_key, "anthropic-version": API_VERSION}
        try:
            response = httpx.request(method, f"{API_URL}{path}", headers=headers,
                                     json=body, timeout=600)
        except httpx.ConnectError as error:
            raise ProviderError("Can't reach api.anthropic.com. Is the internet connected?") from error
        except httpx.HTTPError as error:
            raise ProviderError(f"The request to Anthropic failed: {type(error).__name__}") from error

        if response.status_code in (401, 403):
            raise ProviderError("Anthropic refused the API key. Check the key in Settings.")
        if response.status_code == 404:
            raise ProviderError(f'Anthropic doesn\'t know the model "{self.model}". '
                                "Choose one from the list in Settings.")
        if response.status_code == 429:
            raise ProviderError("Anthropic's rate limit was reached. Wait a minute, or score "
                                "fewer jobs at a time.")
        if response.status_code == 529:
            raise ProviderError("Anthropic is overloaded right now. Try again in a few minutes.")
        if response.status_code >= 400:
            # Anthropic's own explanation (for example "credit balance too low").
            try:
                detail = response.json().get("error", {}).get("message", "")
            except ValueError:
                detail = response.text[:200]
            raise ProviderError(f"Anthropic answered with error {response.status_code}: {detail}")
        return response.json()
