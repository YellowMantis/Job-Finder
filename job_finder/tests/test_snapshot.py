"""Tests for the shared snapshot (snapshot.py) and updating from it
(pipeline.update_from_snapshot, refresh_listings). The snapshot is made here
and "served" by a fake; nothing is downloaded."""

import gzip
import json

import httpx
import pytest

import pipeline
import snapshot

JOBS = [{"company": "Acme", "title": "Engineer", "url": "https://acme/1", "field": "software",
         "level": "not stated", "level_reason": "", "industries": {}, "points": [[32.8, 35.0]],
         "updated": "2026-10-18"}]
COMPANIES = [{"name": "Acme", "greenhouseId": "acme"}, {"name": "NoBoards"}]


@pytest.fixture
def data(tmp_path, monkeypatch):
    for module, name, file in [
        (snapshot, "ETAG_PATH", "snapshot_etag.json"), (pipeline, "JOBS_PATH", "jobs.json"),
        (pipeline, "BOARDS_PATH", "company_boards.json"), (pipeline, "POSTINGS_PATH", "postings.json"),
        (pipeline, "MISSING_PATH", "missing.json"),
    ]:
        monkeypatch.setattr(module, name, tmp_path / file)
    monkeypatch.setattr(snapshot, "DATA_DIR", tmp_path)
    import preferences
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", tmp_path / "preferences.json")
    return tmp_path


def serve(monkeypatch, status, contents=None, etag="abc"):
    """Fake the snapshot's address. Returns the headers each request sent."""
    seen = []

    def fake_get(url, headers, follow_redirects, timeout):
        seen.append(headers)
        body = gzip.compress(json.dumps(contents).encode()) if contents is not None else b""
        return httpx.Response(status, request=httpx.Request("GET", url), content=body,
                              headers={"etag": etag})
    monkeypatch.setattr(snapshot.httpx, "get", fake_get)
    return seen


def test_a_snapshot_holds_jobs_and_board_ids_but_nothing_personal(tmp_path):
    contents = snapshot.build(JOBS, COMPANIES)
    assert contents["format"] == snapshot.FORMAT and contents["jobs"] == JOBS
    assert contents["companies"] == {"Acme": {"greenhouseId": "acme"}}   # only companies with boards
    snapshot.write(contents, tmp_path / "s.json.gz")
    assert json.loads(gzip.decompress((tmp_path / "s.json.gz").read_bytes())) == contents


def test_an_unchanged_snapshot_isnt_downloaded_again(data, monkeypatch):
    seen = serve(monkeypatch, 200, snapshot.build(JOBS, COMPANIES), etag="v1")
    assert snapshot.download()["jobs"] == JOBS
    serve_again = serve(monkeypatch, 304, etag="v1")
    assert snapshot.download() is None
    assert serve_again[0] == {"If-None-Match": "v1"}   # asked "has it changed since v1?"
    assert seen[0] == {}                                # the first time, nothing to compare


@pytest.mark.parametrize("status, contents, reason", [
    (404, None, "answered 404"),                          # not published (or repository private)
    (200, {"format": snapshot.FORMAT + 1}, "newer"),       # a format this app doesn't know
])
def test_an_unusable_snapshot_says_why(data, monkeypatch, status, contents, reason):
    serve(monkeypatch, status, contents)
    with pytest.raises(snapshot.Unavailable, match=reason):
        snapshot.download()


def test_a_damaged_or_unreachable_snapshot_is_unavailable(data, monkeypatch):
    monkeypatch.setattr(snapshot.httpx, "get", lambda *a, **k: httpx.Response(
        200, request=httpx.Request("GET", "x"), content=b"not gzip"))
    with pytest.raises(snapshot.Unavailable, match="damaged"):
        snapshot.download()

    def offline(*args, **kwargs):
        raise httpx.ConnectError("no internet")
    monkeypatch.setattr(snapshot.httpx, "get", offline)
    with pytest.raises(snapshot.Unavailable):
        snapshot.download()


def test_an_update_from_the_snapshot_reads_only_the_boards_it_needs(data, monkeypatch):
    serve(monkeypatch, 200, snapshot.build(JOBS, COMPANIES))
    asked = []

    def read_boards(company, offices):
        asked.append(company["name"])
        listing = {**JOBS[0], "url": "https://boards/acme/1"}
        return [(listing, {"text": "From the job board", "location": "", "apply_url": ""})]
    monkeypatch.setattr(pipeline, "_read_boards", read_boards)

    summary = pipeline.update_from_snapshot({"done": 0, "total": 0})

    assert asked == ["Acme"]
    postings = json.loads((data / "postings.json").read_text())
    assert postings["https://acme/1"]["text"] == "From the job board"
    assert summary["jobs"] == 1 and summary["new_postings"] == 1


def test_without_a_snapshot_the_full_update_is_used(data, monkeypatch):
    serve(monkeypatch, 404)
    monkeypatch.setattr(pipeline, "update_jobs", lambda progress: {"full": True})
    assert pipeline.refresh_listings({"done": 0, "total": 0}) == {"full": True}
