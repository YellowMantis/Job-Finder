"""Claude, through Claude Code and your Claude subscription.

This starts Claude Code in "print" mode: a short, non-interactive session with
no chat window, no tools and no access to your files. Usage counts towards
your Claude plan's limits; the pay-per-use price is recorded only as a guide.

Batches: every Claude Code session has a fixed start-up cost in tokens, so
several jobs share one session, which makes each job much cheaper.
"""

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from providers.base import Provider, ProviderError
from settings import CLAUDE_BATCH_SIZE, NO_WINDOW


def find_claude():
    """Return the path of the Claude Code program, or None if it isn't installed.

    It may be on the PATH (installed on its own), or inside the VS Code
    extension, in which case we take the newest installed version."""
    found = shutil.which("claude")
    if found:
        return found
    extensions = Path.home() / ".vscode" / "extensions"
    candidates = sorted(extensions.glob("anthropic.claude-code-*/resources/native-binary/claude*"))
    return str(candidates[-1]) if candidates else None


class ClaudeCode(Provider):
    id = "claude"
    label = "Claude, through Claude Code"
    reviewer_prefix = "Claude"
    batch_size = CLAUDE_BATCH_SIZE

    def ask(self, system_prompt, prompt, schema):
        """The prompt goes in through standard input rather than the command
        line, because Windows limits a command line to about 32,000 characters."""
        claude = find_claude()
        if claude is None:
            raise ProviderError("Claude Code isn't installed, so jobs can't be scored with Claude.")

        command = [claude, "-p", "--output-format", "json",
                   "--system-prompt", system_prompt,  # replaces Claude Code's long default prompt
                   "--tools", "",                     # no tools: it can only answer
                   "--no-session-persistence",        # don't save this as a chat
                   "--json-schema", json.dumps(schema)]
        # Run in an empty temporary folder, so nothing in your files can be picked up.
        started = time.monotonic()
        with tempfile.TemporaryDirectory() as empty_folder:
            finished = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                      encoding="utf-8", timeout=900, cwd=empty_folder,
                                      creationflags=NO_WINDOW)
        if finished.returncode != 0:
            raise ProviderError(f"Claude Code stopped with an error: {finished.stderr.strip()[:300]}")

        reply = json.loads(finished.stdout)
        if reply.get("is_error"):
            raise ProviderError(f"Claude Code reported an error: {str(reply.get('result'))[:300]}")

        usage = reply.get("usage", {})
        models = reply.get("modelUsage", {})
        # The model that did the work is the one that wrote the most.
        model = max(models, key=lambda name: models[name].get("outputTokens", 0)) if models else "Claude"
        return reply.get("structured_output"), {
            "model": model,
            "input_tokens": usage.get("input_tokens", 0),
            "cache_write_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            # What this would cost at pay-per-use prices. On a subscription it is
            # not charged, but counts towards your usage limits.
            "cost_equivalent_usd": round(reply.get("total_cost_usd") or 0, 4),
            "seconds": round(time.monotonic() - started),
        }
