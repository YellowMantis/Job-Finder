"""A model running on your own PC through Ollama (https://ollama.com).

Free, private (your CV never leaves the machine) and without daily limits, but
small local models read postings much less carefully than Claude. One job per
request by default: small models lose track in long prompts.
"""

import time

import httpx

from providers.base import Provider, ProviderError, outside_text
from settings import OLLAMA_ADDRESS, OLLAMA_BATCH_SIZE


def _get(path, **options):
    try:
        response = httpx.get(f"{OLLAMA_ADDRESS}{path}", timeout=10, **options)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError as error:
        raise ProviderError("Ollama is not running. Start Ollama and try again.") from error
    except httpx.HTTPError as error:
        raise ProviderError(f"Ollama answered with an error: {outside_text(error)}") from error


def installed_models():
    """The models Ollama has downloaded, e.g. ["llama3.1:8b"]."""
    return sorted(model["name"] for model in _get("/api/tags").get("models", []))


class Ollama(Provider):
    id = "ollama"
    label = "a model on this PC, through Ollama"
    reviewer_prefix = "Ollama"
    batch_size = OLLAMA_BATCH_SIZE

    def __init__(self, model=""):
        self.model = model

    def list_models(self):
        return installed_models()

    def ask(self, system_prompt, prompt, schema):
        started = time.monotonic()
        try:
            response = httpx.post(f"{OLLAMA_ADDRESS}/api/chat", timeout=600, json={
                "model": self.model,
                "messages": [{"role": "system", "content": system_prompt},
                             {"role": "user", "content": prompt}],
                "stream": False,
                # Passing the shape makes the model reply with JSON that matches it.
                "format": schema,
                # temperature 0: the same input gives the same answer.
                # num_ctx: room for long postings plus the CV.
                "options": {"temperature": 0, "num_ctx": 16384},
            })
            response.raise_for_status()
        except httpx.ConnectError as error:
            raise ProviderError("Ollama is not running. Start Ollama and try again.") from error
        except httpx.HTTPError as error:
            raise ProviderError(f"Ollama answered with an error: {outside_text(error)}") from error

        reply = response.json()
        return reply["message"]["content"], {
            "model": self.model,
            "input_tokens": reply.get("prompt_eval_count", 0),
            "output_tokens": reply.get("eval_count", 0),
            "seconds": round(time.monotonic() - started),
        }
