"""The scoring providers: one class per kind of AI service.

claude_code.py, ollama.py and openai_compatible.py each do what base.py
describes. Which one is used, with which model and key, is decided by your AI
connections (connections.py).
"""

from providers.base import Provider, ProviderError

__all__ = ["Provider", "ProviderError"]
