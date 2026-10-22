"""Tests for offering new versions of the app (updates.py). GitHub's answer is
a recorded one; nothing is downloaded or installed."""

import httpx
import pytest

import updates


def github_answers(monkeypatch, status, release=None):
    def fake_get(url, timeout, headers):
        assert url == updates.LATEST_RELEASE_URL
        return httpx.Response(status, request=httpx.Request("GET", url), json=release or {})
    monkeypatch.setattr(updates.httpx, "get", fake_get)


RELEASE = {
    "tag_name": "v0.2.0", "body": "- Faster updates\n- Score one job",
    "html_url": "https://github.com/YellowMantis/Job-Finder/releases/tag/v0.2.0",
    "assets": [{"name": "Job-Finder-mac.dmg", "browser_download_url": "https://x/mac"},
               {"name": "Job-Finder-Setup.exe",
                "browser_download_url": "https://github.com/YellowMantis/Job-Finder/releases/download/v0.2.0/Job-Finder-Setup.exe"}],
}


def test_versions_compare_as_numbers():
    assert updates.version_tuple("v1.10.0") > updates.version_tuple("1.9.3")
    assert updates.version_tuple("0.2.0") == (0, 2, 0)


def test_a_newer_release_is_offered(monkeypatch):
    github_answers(monkeypatch, 200, RELEASE)
    update = updates.check("0.1.0")
    assert update["version"] == "0.2.0"
    assert update["installer"].endswith("/Job-Finder-Setup.exe")
    assert "Score one job" in update["notes"]


@pytest.mark.parametrize("current", ["0.2.0", "0.3.1"])
def test_the_same_or_an_older_release_is_not_offered(monkeypatch, current):
    github_answers(monkeypatch, 200, RELEASE)
    assert updates.check(current) is None


def test_a_private_or_unreachable_repository_offers_nothing(monkeypatch):
    github_answers(monkeypatch, 404)
    assert updates.check("0.1.0") is None

    def offline(url, timeout, headers):
        raise httpx.ConnectError("no internet")
    monkeypatch.setattr(updates.httpx, "get", offline)
    assert updates.check("0.1.0") is None


def test_an_installer_from_anywhere_else_is_refused(monkeypatch):
    monkeypatch.setattr(updates.sys, "platform", "win32")
    with pytest.raises(ValueError, match="isn't this project's GitHub Releases"):
        updates.install({"installer": "https://evil.example.com/Job-Finder-Setup.exe", "page": ""})
