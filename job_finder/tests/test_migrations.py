"""Tests for keeping data working across app updates (migrations.py). Each
test builds a data folder in the old shape in a throwaway folder."""

import json

import pytest

import migrations


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(migrations, "DATA_DIR", tmp_path)
    monkeypatch.setattr(migrations, "BACKUPS_DIR", tmp_path / "backups")
    return tmp_path


def write(folder, name, data):
    (folder / name).write_text(json.dumps(data), encoding="utf-8")


def read(folder, name):
    return json.loads((folder / name).read_text(encoding="utf-8"))


def test_a_new_user_starts_at_the_current_version(folder):
    assert migrations.run() is None
    assert read(folder, "data_version.json")["version"] == migrations.CURRENT_VERSION
    assert not (folder / "backups").exists()


def test_data_from_before_versions_is_upgraded_and_backed_up_first(folder):
    # The shape of data written in October 2026, before versions were kept.
    write(folder, "excluded.json", [{"title": "old"}])
    write(folder, "connections.json", {"active": "c1", "connections": [
        {"id": "c1", "kind": "claude", "name": "Claude Code"}]})
    write(folder, "scoring_log.json", [{"time": "2026-10-17 03:21", "jobs": 4},
                                       {"time": "2026-10-18 12:00", "jobs": 1, "connection": "c2"}])

    assert migrations.run() is None

    assert not (folder / "excluded.json").exists()
    log = read(folder, "scoring_log.json")
    assert log[0]["connection"] == "c1"          # filled in
    assert log[1]["connection"] == "c2"          # left as it was
    assert read(folder, "data_version.json")["version"] == migrations.CURRENT_VERSION
    [backup] = (folder / "backups").iterdir()
    assert read(backup, "scoring_log.json")[0] == {"time": "2026-10-17 03:21", "jobs": 4}


def test_running_again_changes_nothing(folder):
    write(folder, "scoring_log.json", [{"time": "2026-10-17 03:21", "jobs": 4}])
    migrations.run()
    before = (folder / "scoring_log.json").read_text(encoding="utf-8")
    migrations.run()
    assert (folder / "scoring_log.json").read_text(encoding="utf-8") == before
    assert len(list((folder / "backups").iterdir())) == 1   # backed up only when migrating


def test_data_from_a_newer_app_is_left_untouched(folder):
    write(folder, "data_version.json", {"version": migrations.CURRENT_VERSION + 1})
    write(folder, "jobs.json", [{"title": "kept"}])
    problem = migrations.run()
    assert "newer version of Job Finder" in problem
    assert read(folder, "jobs.json") == [{"title": "kept"}]
