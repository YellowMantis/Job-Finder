"""Any AI service that speaks the OpenAI chat format: OpenAI itself, Groq,
OpenRouter, or a model on your own PC through LM Studio or Ollama.

Requests go straight from your computer to the service you chose, with your
own key (kept in your system's password safe, see connections.py), sent
only to that service's address. It is never written to a log, a message or a
file.

The answer's shape: the request asks the service to follow our JSON schema
exactly. Some services or models can't, and refuse that request; then it is
sent once more asking only for JSON, with the schema written into the
instructions instead. Either way scoring.py checks the answer afterwards.
"""

import json
import time

import httpx

from providers.base import Provider, ProviderError, outside_text
from settings import API_BATCH_SIZE


class OpenAICompatible(Provider):
    id = "api"
    label = "an OpenAI-compatible API"  # replaced by the service and model, below
    reviewer_prefix = "API"
    batch_size = API_BATCH_SIZE

    def __init__(self, name, base_url, model, api_key=""):
        """name: the service's name for messages ("Groq"); base_url: its address
        ("https://api.groq.com/openai/v1"); api_key: "" for a service on this PC."""
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.label = f"{model or 'no model chosen'} through {name}"
        self.reviewer_prefix = name  # reviews are signed "Groq (model)"

    def list_models(self):
        """The models this service offers, for choosing from a list."""
        reply = self._request("GET", "/models")
        return sorted(model["id"] for model in reply.get("data", []))

    def ask(self, system_prompt, prompt, schema):
        if not self.model:
            raise ProviderError(f"Choose a model for {self.name} first.")
        started = time.monotonic()
        strict = {"type": "json_schema",
                  "json_schema": {"name": "answer", "schema": schema, "strict": False}}
        try:
            reply = self._send(system_prompt, prompt, strict)
        except _ShapeNotSupported:
            loose_system = (f"{system_prompt}\n\nAnswer with JSON only, following this JSON "
                            f"schema exactly:\n{json.dumps(schema)}")
            reply = self._send(loose_system, prompt, {"type": "json_object"})

        usage = reply.get("usage") or {}
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        return reply["choices"][0]["message"]["content"], {
            "model": reply.get("model") or self.model,
            # Cached tokens are part of the prompt tokens; count them only once.
            "input_tokens": (usage.get("prompt_tokens") or 0) - cached,
            "cache_read_tokens": cached,
            "output_tokens": usage.get("completion_tokens") or 0,
            "seconds": round(time.monotonic() - started),
        }

    def _send(self, system_prompt, prompt, response_format):
        return self._request("POST", "/chat/completions", {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": prompt}],
            "temperature": 0,  # the same input gives the same answer
            "response_format": response_format,
        })

    def _request(self, method, path, body=None):
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            response = httpx.request(method, f"{self.base_url}{path}", headers=headers,
                                     timeout=600, json=body)
        except httpx.ConnectError as error:
            raise ProviderError(f"Can't reach {self.base_url}. Is the service running, "
                                "and is the address right?") from error
        except httpx.HTTPError as error:
            raise ProviderError(f"The request to {self.base_url} failed: "
                                f"{type(error).__name__}") from error

        schema_requested = (body or {}).get("response_format", {}).get("type") == "json_schema"
        if response.status_code == 400 and schema_requested:
            raise _ShapeNotSupported()
        if response.status_code in (401, 403):
            raise ProviderError(f"{self.name} refused the API key. Check the key in Settings.")
        if response.status_code == 404:
            raise ProviderError(f'{self.name} doesn\'t know the model "{self.model}", or the '
                                "address is wrong. Check the connection in Settings.")
        if response.status_code == 429:
            raise ProviderError("The service's rate or usage limit was reached. Wait a while, "
                                "or score fewer jobs at a time.")
        if response.status_code >= 400:
            # The service's own explanation, shortened, with anything key-like hidden.
            raise ProviderError(f"The service answered with error {response.status_code}: "
                                f"{outside_text(response.text)}")
        return response.json()


class _ShapeNotSupported(Exception):
    """The service refused to enforce our JSON schema; ask for plain JSON instead."""
