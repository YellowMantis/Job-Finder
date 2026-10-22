"""What every scoring provider must do.

A provider is one kind of AI service that can read job postings for us:
Claude through Claude Code, a local model through Ollama, or any service that
speaks the OpenAI format. The rest of the app never talks to an AI directly; it
calls ask() on the provider of the AI connection in use (connections.py). To
add a kind of service, write one class with ask() and use it in
connections.provider_for(). Everything else (the prompt, checking the answer, the
score, the log) is shared, in scoring.py and fit_rules.py.
"""

import re

# Anything that looks like a key or token: a known key's start, or a long run of
# letters and digits with no spaces (no real word is that long).
KEY_LIKE = re.compile(r"\b(?:sk-ant-|sk-|gsk_|AIza|xai-|hf_)[\w-]{6,}|[\w-]{32,}")


class Provider:
    id = ""               # the connection kind it serves: "claude", "ollama" or "api"
    label = ""            # how the page names it; set to the connection's name
    reviewer_prefix = ""  # each review is signed "<prefix> (<model>)": the connection's name
    batch_size = 1        # how many jobs it reviews per request
    requests_at_once = 1  # how many batches may run at the same time
    connection_id = ""    # the AI connection it belongs to (connections.py), for the log

    def list_models(self):
        """The models one can choose from, or [] if there's no choice to make."""
        return []

    def ask(self, system_prompt, prompt, schema):
        """Send one request and return (answer, usage).

        system_prompt  the instructions (who the AI is, what to do)
        prompt         the material: the CV and the job postings
        schema         the JSON schema the answer must follow
        answer         the AI's reply: a dict, or JSON text (checked later by the caller)
        usage          what the request used, as far as the service says:
                       {"model", "input_tokens", "output_tokens",
                        "cache_write_tokens", "cache_read_tokens",
                        "cost_equivalent_usd", "seconds"}; missing keys count as 0

        Raise ProviderError with a plain message if the service can't be used.
        """
        raise NotImplementedError


class ProviderError(Exception):
    """The provider can't be used right now; the message says why, for the page."""


def outside_text(text, limit=200):
    """Text from outside the app, such as a service's error reply, made safe to
    show on the page: on one line, shortened, and with anything that looks like
    a key hidden, in case a service ever repeats one back."""
    return KEY_LIKE.sub("[hidden]", " ".join(str(text).split())[:limit])
