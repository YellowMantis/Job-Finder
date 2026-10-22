"""Your AI connections: the AIs you added for scoring, and which one is in use.

A connection is one way to reach an AI: Claude Code, a model on this PC
through Ollama, or a service with your key (OpenAI, Groq, LM Studio...).
You can add several and switch between them at any time; each score records
which connection made it.

Where things are kept:
  data/connections.json   the list: names, kinds, addresses, models. No keys.
  your system's password safe (Windows Credential Manager, macOS Keychain),
                          through the keyring library: the keys. They are
                          stored encrypted under your own login, outside the
                          project folder, so they can't reach GitHub or a zip
                          of the folder.

Keys only ever leave this file as a masked hint ("gsk_…3f9a").
"""

import hashlib
import json
import re

import keyring
from keyring.errors import KeyringError

from providers import ProviderError
from providers.anthropic_api import AnthropicAPI
from providers.claude_code import ClaudeCode
from providers.ollama import Ollama
from providers.openai_compatible import OpenAICompatible
from settings import DATA_DIR

CONNECTIONS_PATH = DATA_DIR / "connections.json"
# The name keys are filed under in the password safe. It includes a short
# fingerprint of the data folder, because the desktop app and a copy run from the
# source code keep separate connection lists: connection "c1" of one must never
# pick up the key of "c1" in the other.
KEYRING_SERVICE = "job-finder-" + hashlib.sha1(str(DATA_DIR.resolve()).encode()).hexdigest()[:8]

KINDS = {"claude": "Claude Code", "anthropic": "Claude API", "ollama": "Ollama on this PC",
         "api": "An AI service"}

# Services that speak the OpenAI chat format: their name and address.
SERVICES = {
    "openai": ("OpenAI", "https://api.openai.com/v1"),
    "groq": ("Groq", "https://api.groq.com/openai/v1"),
    "openrouter": ("OpenRouter", "https://openrouter.ai/api/v1"),
    "lmstudio": ("LM Studio", "http://localhost:1234/v1"),
}

# The services offered for "an AI service with your key", as the page lists them.
# Anthropic has its own kind of connection (anthropic_api.py); the rest speak the
# OpenAI format.
PAGE_SERVICES = {"anthropic": "Anthropic (Claude API)",
                 **{key: name for key, (name, _) in SERVICES.items()}}


# ---- The list --------------------------------------------------------------------

def load():
    """{"active": connection id or None, "connections": [...]}"""
    if CONNECTIONS_PATH.exists():
        return json.loads(CONNECTIONS_PATH.read_text(encoding="utf-8"))
    return {"active": None, "connections": []}


def _save(data):
    DATA_DIR.mkdir(exist_ok=True)
    CONNECTIONS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _find(data, connection_id):
    for connection in data["connections"]:
        if connection["id"] == connection_id:
            return connection
    raise ProviderError("That AI connection doesn't exist any more.")


def check(fields):
    """Return what is wrong with a new or changed connection, or None.
    Everything here ends up in requests, so only known shapes pass."""
    if fields.get("kind") not in KINDS:
        return f'"kind" must be one of: {", ".join(KINDS)}'
    if not str(fields.get("name", "")).strip():
        return "Give the connection a name."
    if fields["kind"] == "api":
        service = fields.get("service")
        if service not in SERVICES and service != "custom":
            return f'"service" must be one of: {", ".join(SERVICES)}, custom'
        if service == "custom" and not re.match(r"^https?://\S+$", fields.get("base_url", "")):
            return "A custom service needs its address, starting with http:// or https://"
        if not fields.get("model"):
            return "Choose a model."
    if fields["kind"] in ("ollama", "anthropic") and not fields.get("model"):
        return "Choose a model."
    return None


def add(fields, key=""):
    """Add a connection, keep its key in the password safe, and use it from now
    on. Returns the new connection's id."""
    data = load()
    taken = {connection["id"] for connection in data["connections"]}
    number = 1
    while f"c{number}" in taken:
        number += 1
    connection = {"id": f"c{number}", **_clean(fields)}
    if key:
        _store_key(connection["id"], key)
    data["connections"].append(connection)
    data["active"] = connection["id"]
    _save(data)
    return connection["id"]


def update(connection_id, fields, key=None):
    """Change a connection. key=None keeps the stored key; "" removes it."""
    data = load()
    connection = _find(data, connection_id)
    connection.update(_clean(fields))
    if key is not None:
        _store_key(connection_id, key) if key else _forget_key(connection_id)
    _save(data)


def remove(connection_id):
    data = load()
    _find(data, connection_id)
    data["connections"] = [c for c in data["connections"] if c["id"] != connection_id]
    if data["active"] == connection_id:
        data["active"] = data["connections"][0]["id"] if data["connections"] else None
    _forget_key(connection_id)
    _save(data)


def activate(connection_id):
    data = load()
    _find(data, connection_id)
    data["active"] = connection_id
    _save(data)


def calibrate(connection_id, percent, tokens):
    """Remember how much of a Claude plan's 5-hour allowance tokens cost: you
    typed the session % that Claude Code's /usage shows, after this app used
    `tokens` in the same 5 hours. The % also counts anything else you did with
    Claude in that time, so estimates from it lean high, never low."""
    data = load()
    connection = _find(data, connection_id)
    connection["calibration"] = {"percent_per_1k_tokens": round(percent / (tokens / 1000), 4),
                                 "percent": percent, "tokens": tokens}
    _save(data)


def _clean(fields):
    """Only the fields a connection has; the address comes from the service list."""
    kept = {key: str(fields.get(key, "")).strip()
            for key in ["name", "kind", "service", "base_url", "model"]}
    if kept["kind"] == "api" and kept["service"] in SERVICES:
        kept["base_url"] = SERVICES[kept["service"]][1]
    if kept["kind"] == "anthropic":
        kept["service"], kept["base_url"] = "anthropic", ""
    return kept


# ---- Keys --------------------------------------------------------------------------

def _store_key(connection_id, key):
    try:
        keyring.set_password(KEYRING_SERVICE, connection_id, key)
    except KeyringError as error:
        raise ProviderError("Your system's password safe couldn't store the key.") from error


def _forget_key(connection_id):
    try:
        keyring.delete_password(KEYRING_SERVICE, connection_id)
    except KeyringError:
        pass  # there was no key


def get_key(connection_id):
    """The connection's key from the password safe, or "" if it has none."""
    try:
        return keyring.get_password(KEYRING_SERVICE, connection_id) or ""
    except KeyringError:
        return ""


def mask(key):
    """"gsk_abc…3f9a": enough to recognise a key, too little to use it."""
    if not key:
        return ""
    return f"{key[:4]}…{key[-4:]}" if len(key) > 12 else "…"


def for_page():
    """The list as the page sees it: keys only as masked hints."""
    data = load()
    return {"active": data["active"], "connections": [
        {**connection, "key_hint": mask(get_key(connection["id"]))}
        for connection in data["connections"]]}


# ---- From a connection to a provider ------------------------------------------------

def provider_for(connection, key=None):
    """The provider that talks to this connection's AI."""
    kind = connection["kind"]
    if kind == "claude":
        provider = ClaudeCode()
    elif kind == "ollama":
        provider = Ollama(connection["model"])
    elif kind == "anthropic":
        provider = AnthropicAPI(connection["model"],
                                get_key(connection.get("id", "")) if key is None else key)
    else:
        provider = OpenAICompatible(connection["name"], connection["base_url"], connection["model"],
                                    get_key(connection["id"]) if key is None else key)
    provider.connection_id = connection.get("id", "")
    provider.label = connection["name"]
    provider.reviewer_prefix = connection["name"]  # scores are signed "<name> (<model>)"
    return provider


def active_provider():
    """The provider of the connection in use. ProviderError if there is none."""
    data = load()
    if not data["active"]:
        raise ProviderError("Choose who scores the fit first: add an AI connection in Settings.")
    return provider_for(_find(data, data["active"]))
