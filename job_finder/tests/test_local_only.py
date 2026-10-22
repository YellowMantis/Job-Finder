"""Tests that only the app's own page can use it (only_this_apps_page in app.py).

Any website open in your browser can send requests to 127.0.0.1. These are the
requests such a site would send, and each must be refused before it is answered.
"""

import pytest

import app


@pytest.fixture
def client():
    return app.app.test_client()


@pytest.mark.parametrize("base_url, headers", [
    ("http://127.0.0.1:5000", {}),                                        # the app's own window
    ("http://localhost:5173", {"Origin": "http://localhost:5173"}),       # the page while developing
    ("http://127.0.0.1:61234", {"Origin": "http://127.0.0.1:61234",       # the desktop app's free port
                                "Sec-Fetch-Site": "same-origin"}),
])
def test_the_apps_own_page_is_answered(client, base_url, headers):
    assert client.get("/api/fit/status", base_url=base_url, headers=headers).status_code == 200


def test_dns_rebinding_is_refused(client):
    # The browser thinks 127.0.0.1 is "evil.example", so it sends that name.
    answer = client.get("/api/cv/sent", base_url="http://evil.example:5000")
    assert answer.status_code == 403 and "own page" in answer.get_json()["error"]


@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.example"},          # a form or script on another site
    {"Origin": "null"},                          # a sandboxed frame or a file on disk
    {"Sec-Fetch-Site": "cross-site"},            # the browser says another site sent it
])
def test_requests_from_other_sites_are_refused(client, headers):
    answer = client.post("/api/fit/stop", base_url="http://127.0.0.1:5000", headers=headers)
    assert answer.status_code == 403


def test_a_cv_cant_be_replaced_from_another_site(client):
    answer = client.post("/api/cv", base_url="http://127.0.0.1:5000",
                         headers={"Origin": "https://evil.example"},
                         data={}, content_type="multipart/form-data")
    assert answer.status_code == 403
