"""Tests for downloading techmap without Git (download.py): a small zip made
here stands in for GitHub's, and the data folder is a throwaway one."""

import io
import zipfile

import httpx
import pytest

import download


def zip_of(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture
def without_git(tmp_path, monkeypatch):
    monkeypatch.setattr(download.shutil, "which", lambda program: None)
    monkeypatch.setattr(download, "TECHMAP_DIR", tmp_path / "techmap")
    return tmp_path / "techmap"


def serve(monkeypatch, files):
    monkeypatch.setattr(download.httpx, "get", lambda url, **options: httpx.Response(
        200, request=httpx.Request("GET", url), content=zip_of(files)))


def test_only_the_data_is_unpacked(without_git, monkeypatch):
    serve(monkeypatch, {
        "techmap-main/categories.json": "{}",
        "techmap-main/companies/1.json": '{"name": "Acme"}',
        "techmap-main/jobs/software.csv": "company,title",
        "techmap-main/logos/acme.webp": "a big picture",
    })
    download.download_data()
    assert (without_git / "categories.json").exists()
    assert (without_git / "companies" / "1.json").read_text() == '{"name": "Acme"}'
    assert (without_git / "jobs" / "software.csv").exists()
    assert not (without_git / "logos").exists()


def test_a_new_download_replaces_the_old_data(without_git, monkeypatch):
    serve(monkeypatch, {"techmap-main/jobs/old.csv": "x"})
    download.download_data()
    serve(monkeypatch, {"techmap-main/jobs/new.csv": "y"})
    download.download_data()
    assert (without_git / "jobs" / "new.csv").exists()
    assert not (without_git / "jobs" / "old.csv").exists()


def test_a_failed_download_keeps_the_old_data(without_git, monkeypatch):
    serve(monkeypatch, {"techmap-main/jobs/old.csv": "x"})
    download.download_data()

    def broken(url, **options):
        raise httpx.ConnectError("no internet")
    monkeypatch.setattr(download.httpx, "get", broken)
    with pytest.raises(httpx.ConnectError):
        download.download_data()
    assert (without_git / "jobs" / "old.csv").exists()


def test_a_path_escaping_the_folder_is_never_written(without_git, monkeypatch, tmp_path):
    serve(monkeypatch, {"techmap-main/../../evil.txt": "x", "techmap-main/jobs/a.csv": "y"})
    download.download_data()
    assert not (tmp_path.parent / "evil.txt").exists()
    assert not (tmp_path / "evil.txt").exists()
