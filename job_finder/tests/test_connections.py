"""Tests for AI connections (connections.py and its /api/connections addresses).

The list is written to a throwaway folder, and the system's password safe is
replaced by a fake one, so your real Windows Credential Manager is never
touched."""

import json

import pytest

import connections
from providers import ProviderError

KEY = "gsk_abcdefghijklmnop3f9a"
GROQ = {"name": "Groq (free key)", "kind": "api", "service": "groq", "model": "big-model"}


class FakeSafe:
    """Stands in for the keyring library: keeps keys in a dictionary."""
    def __init__(self):
        self.keys = {}

    def set_password(self, service, name, key):
        self.keys[(service, name)] = key

    def get_password(self, service, name):
        return self.keys.get((service, name))

    def delete_password(self, service, name):
        self.keys.pop((service, name), None)


@pytest.fixture
def safe(tmp_path, monkeypatch):
    fake = FakeSafe()
    monkeypatch.setattr(connections, "keyring", fake)
    monkeypatch.setattr(connections, "CONNECTIONS_PATH", tmp_path / "connections.json")
    monkeypatch.setattr(connections, "DATA_DIR", tmp_path)
    return fake


def test_with_no_connections_scoring_asks_you_to_add_one(safe):
    with pytest.raises(ProviderError, match="add an AI connection"):
        connections.active_provider()


def test_a_new_connection_is_used_and_its_key_kept_in_the_safe(safe, tmp_path):
    connection_id = connections.add(GROQ, KEY)

    assert connections.load()["active"] == connection_id
    assert safe.keys[(connections.KEYRING_SERVICE, connection_id)] == KEY
    assert connections.KEYRING_SERVICE.startswith("job-finder-")
    # The list file holds no key, and the address comes from the service list.
    saved = (tmp_path / "connections.json").read_text(encoding="utf-8")
    assert KEY not in saved
    assert json.loads(saved)["connections"][0]["base_url"] == "https://api.groq.com/openai/v1"


def test_the_page_sees_only_a_masked_key(safe):
    connections.add(GROQ, KEY)
    shown = connections.for_page()["connections"][0]
    assert shown["key_hint"] == "gsk_…3f9a"
    assert KEY not in json.dumps(connections.for_page())


def test_the_active_provider_uses_the_connection_and_its_key(safe):
    connections.add({"name": "Claude Code", "kind": "claude"})
    groq_id = connections.add(GROQ, KEY)
    provider = connections.active_provider()
    assert provider.api_key == KEY and provider.model == "big-model"
    assert provider.reviewer_prefix == "Groq (free key)"   # scores are signed with its name
    assert provider.connection_id == groq_id


def test_switching_connections(safe):
    claude_id = connections.add({"name": "Claude Code", "kind": "claude"})
    connections.add(GROQ, KEY)
    connections.activate(claude_id)
    assert connections.active_provider().id == "claude"


def test_removing_a_connection_forgets_its_key_and_picks_another(safe):
    claude_id = connections.add({"name": "Claude Code", "kind": "claude"})
    groq_id = connections.add(GROQ, KEY)
    connections.remove(groq_id)
    assert (connections.KEYRING_SERVICE, groq_id) not in safe.keys
    assert connections.load()["active"] == claude_id


def test_updating_without_a_key_keeps_the_stored_one(safe):
    groq_id = connections.add(GROQ, KEY)
    connections.update(groq_id, {**GROQ, "model": "other-model"})
    assert connections.get_key(groq_id) == KEY
    assert connections.active_provider().model == "other-model"


def test_a_connection_without_a_key_has_none(safe):
    claude_id = connections.add({"name": "Claude Code", "kind": "claude"})
    assert connections.get_key(claude_id) == ""


@pytest.mark.parametrize("fields, problem", [
    ({"name": "x", "kind": "magic"}, '"kind" must be one of'),
    ({"name": "", "kind": "claude"}, "Give the connection a name"),
    ({"name": "x", "kind": "api", "service": "nope", "model": "m"}, '"service" must be one of'),
    ({"name": "x", "kind": "api", "service": "custom", "model": "m",
      "base_url": "file:///etc/passwd"}, "starting with http"),
    ({"name": "x", "kind": "api", "service": "groq"}, "Choose a model"),
    ({"name": "x", "kind": "ollama"}, "Choose a model"),
])
def test_bad_connections_are_refused(fields, problem):
    assert problem in connections.check(fields)


def test_masking_short_and_empty_keys():
    assert connections.mask("") == ""
    assert connections.mask("short") == "…"   # too short to show any of it


# ---- The addresses the page uses -------------------------------------------------------

@pytest.fixture
def client(safe):
    import app
    return app.app.test_client()


def test_adding_through_the_page_never_sends_the_key_back(client):
    answer = client.post("/api/connections", json={"fields": GROQ, "key": KEY})
    assert answer.status_code == 200
    assert KEY not in answer.get_data(as_text=True)
    assert answer.get_json()["connections"][0]["key_hint"] == "gsk_…3f9a"


def test_a_bad_connection_from_the_page_is_refused(client):
    answer = client.post("/api/connections", json={"fields": {"name": "x", "kind": "magic"}})
    assert answer.status_code == 400


def test_switching_is_refused_while_scoring_runs(client):
    import app
    connection_id = client.post("/api/connections", json={"fields": GROQ, "key": KEY}) \
        .get_json()["connections"][0]["id"]
    app.fit_progress["running"] = True
    try:
        assert client.post(f"/api/connections/{connection_id}/activate").status_code == 409
    finally:
        app.fit_progress["running"] = False


def test_status_says_when_no_ai_is_chosen(client):
    assert client.get("/api/status").get_json()["scorer"] is None


def test_models_for_an_edited_connection_use_the_saved_key(client, monkeypatch):
    import app
    connection_id = client.post("/api/connections", json={"fields": GROQ, "key": KEY}) \
        .get_json()["connections"][0]["id"]
    seen = {}

    def fake_provider_for(fields, key):
        seen.update(fields=fields, key=key)

        class Lister:
            def list_models(self):
                return ["m1"]
        return Lister()
    monkeypatch.setattr(app.connections, "provider_for", fake_provider_for)

    answer = client.post("/api/connections/models",
                         json={"id": connection_id, "fields": {**GROQ, "model": "new-model"}})
    assert answer.get_json() == {"models": ["m1"]}
    assert seen["key"] == KEY                       # the saved key, not pasted again
    assert seen["fields"]["model"] == "new-model"   # but the fields being edited


def test_a_claude_api_connection(safe):
    connection_id = connections.add({"name": "Claude API", "kind": "anthropic",
                                     "model": "claude-test-1"}, "sk-ant-key-123456789")
    provider = connections.active_provider()
    assert provider.id == "anthropic" and provider.model == "claude-test-1"
    assert provider.api_key == "sk-ant-key-123456789" and provider.requests_at_once == 3
    assert connections.load()["connections"][0]["service"] == "anthropic"
    assert connection_id == "c1"


def test_a_claude_api_connection_needs_a_model():
    assert "Choose a model" in connections.check({"name": "x", "kind": "anthropic"})


# ---- Calibrating against a Claude plan's /usage % ----------------------------------------

def test_calibration_learns_percent_per_thousand_tokens(client, tmp_path, monkeypatch):
    import scoring
    from datetime import datetime, timedelta
    monkeypatch.setattr(scoring, "SCORING_LOG_PATH", tmp_path / "log.json")
    claude_id = client.post("/api/connections", json={
        "fields": {"name": "Claude Code", "kind": "claude"}}).get_json()["connections"][0]["id"]
    now = datetime.now()
    record = lambda when, tokens, connection=claude_id: {
        "time": when.strftime("%Y-%m-%d %H:%M"), "connection": connection,
        "input_tokens": tokens, "output_tokens": 0}
    (tmp_path / "log.json").write_text(json.dumps([
        record(now - timedelta(hours=1), 20000),
        record(now - timedelta(minutes=10), 20000),
        record(now - timedelta(hours=7), 99999),           # an earlier session: not counted
        record(now, 55555, connection="c9"),              # another connection: not counted
    ]), encoding="utf-8")

    answer = client.post(f"/api/connections/{claude_id}/calibrate", json={"percent": 6})

    calibration = answer.get_json()["connections"][0]["calibration"]
    assert calibration["tokens"] == 40000
    assert calibration["percent_per_1k_tokens"] == 0.15   # 6% / 40 thousand tokens


def test_calibration_needs_a_recent_batch_and_a_sensible_percent(client, tmp_path, monkeypatch):
    import scoring
    monkeypatch.setattr(scoring, "SCORING_LOG_PATH", tmp_path / "empty.json")
    claude_id = client.post("/api/connections", json={
        "fields": {"name": "Claude Code", "kind": "claude"}}).get_json()["connections"][0]["id"]
    assert "Score a batch first" in client.post(f"/api/connections/{claude_id}/calibrate",
                                                json={"percent": 5}).get_json()["error"]
    assert client.post(f"/api/connections/{claude_id}/calibrate",
                       json={"percent": 250}).status_code == 400
