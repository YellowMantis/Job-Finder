"""Tests for the page's light or dark look (/api/theme in app.py). Each test
saves to its own folder, never the real data folder."""

import pytest

import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "APPEARANCE_PATH", tmp_path / "appearance.json")
    return app.app.test_client()


def test_light_until_you_choose(client):
    assert app.saved_theme() == "light"


def test_an_old_follow_windows_choice_becomes_light(client):
    app.write_json(app.APPEARANCE_PATH, {"theme": "system"})
    assert app.saved_theme() == "light"


def test_a_choice_is_saved(client):
    assert client.post("/api/theme", json={"theme": "dark"}).status_code == 200
    assert app.saved_theme() == "dark"


def test_an_unknown_theme_is_refused(client):
    assert client.post("/api/theme", json={"theme": "purple"}).status_code == 400
    assert client.post("/api/theme", data="not json").status_code == 400
    assert app.saved_theme() == "light"


def test_a_chosen_theme_is_written_into_the_page(client, monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text('<!doctype html><html lang="en"><body></body></html>',
                                         encoding="utf-8")
    monkeypatch.setattr(app, "WEB_DIR", tmp_path)
    client.post("/api/theme", json={"theme": "dark"})
    assert 'data-theme="dark"' in client.get("/").get_data(as_text=True)
    client.post("/api/theme", json={"theme": "light"})
    assert 'data-theme="light"' in client.get("/").get_data(as_text=True)
