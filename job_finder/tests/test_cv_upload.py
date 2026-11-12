"""Tests for uploading a CV (POST /api/cv in app.py).

The app's files are pointed at a throwaway folder, and the PDFs are made
here in code, so no real CV is ever needed or touched.
"""

import io
import json

import pytest


def make_pdf(text):
    """A minimal one-page PDF showing one line of text."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, xref)
    return pdf


@pytest.fixture
def client(tmp_path, monkeypatch):
    """The app, with its CV files in a throwaway folder."""
    import app
    monkeypatch.setattr(app, "DATA_DIR", tmp_path)
    monkeypatch.setattr(app, "CV_PDF_PATH", tmp_path / "cv.pdf")
    monkeypatch.setattr(app, "CV_TEXT_PATH", tmp_path / "cv.txt")
    monkeypatch.setattr(app, "CV_INFO_PATH", tmp_path / "cv_info.json")
    monkeypatch.setattr(app, "FITS_PATH", tmp_path / "fits.json")
    return app.app.test_client(), tmp_path


def upload(test_client, data, name="cv.pdf"):
    return test_client.post("/api/cv", data={"cv": (io.BytesIO(data), name)},
                            content_type="multipart/form-data")


def test_a_pdf_is_read(client):
    test_client, folder = client
    answer = upload(test_client, make_pdf("Python developer"))
    assert answer.status_code == 200
    assert "Python developer" in (folder / "cv.txt").read_text(encoding="utf-8")


def test_a_file_that_is_not_a_pdf_is_refused(client):
    test_client, folder = client
    answer = upload(test_client, b"hello, I am not a PDF", name="cv.pdf")
    assert answer.status_code == 400
    assert not (folder / "cv.pdf").exists()


def test_the_same_cv_again_keeps_your_corrected_years(client):
    test_client, folder = client
    upload(test_client, make_pdf("Python developer"))
    test_client.post("/api/cv/years", json={"years": 3})

    upload(test_client, make_pdf("Python developer"))

    info = json.loads((folder / "cv_info.json").read_text(encoding="utf-8"))
    assert info["professional_years"] == 3


def test_a_different_cv_starts_without_years(client):
    test_client, folder = client
    upload(test_client, make_pdf("Python developer"))
    test_client.post("/api/cv/years", json={"years": 3})

    upload(test_client, make_pdf("Java developer with 5 years"))

    info = json.loads((folder / "cv_info.json").read_text(encoding="utf-8"))
    assert "professional_years" not in info


# ---- Suggestions from a new CV ------------------------------------------------------

@pytest.mark.parametrize("years, levels", [
    (0, ["junior", "not stated"]), (2, ["junior", "not stated"]),
    (3, ["not stated"]), (5, ["not stated"]),
    (6, ["senior", "not stated"]), (15, ["senior", "not stated"]),
])
def test_levels_follow_the_years_of_paid_work(years, levels):
    import scoring
    assert scoring.level_for(years) == levels


def test_suggestions_from_a_cv(client, monkeypatch):
    import app
    import preferences
    import scoring
    test_client, folder = client
    upload(test_client, make_pdf("Python developer living in Afula"))
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", folder / "preferences.json")
    monkeypatch.setattr(app, "PREFERENCES_PATH", folder / "preferences.json")
    monkeypatch.setattr(scoring, "SCORING_LOG_PATH", folder / "log.json")

    from providers import Provider

    class FakeAI(Provider):
        id, label, connection_id = "fake", "a fake AI", "c9"

        def ask(self, system_prompt, prompt, schema):
            assert "Python developer living in Afula" in prompt
            assert "home_town" not in prompt   # your town is yours to type, not read from the CV
            return {"professional_years": 1,
                    "fields": ["software", "qa"], "roles": ["Junior Backend Developer"]}, {}
    monkeypatch.setattr(app.connections, "active_provider", lambda: FakeAI())

    answer = test_client.post("/api/cv/suggest").get_json()

    assert answer["preferences"]["home"] is None   # nothing is guessed: you choose it
    assert answer["preferences"]["levels"] == ["junior", "not stated"]
    assert answer["preferences"]["fields"] == ["software", "qa"]
    assert answer["roles"] == ["Junior Backend Developer"]
    # The years are remembered, so scoring needn't ask the AI again.
    assert json.loads((folder / "cv_info.json").read_text(encoding="utf-8"))["professional_years"] == 1
    # Nothing else is saved: setup is still needed until you confirm.
    assert test_client.get("/api/status").get_json()["setup_needed"] is True


def test_suggestions_need_an_ai(client, monkeypatch):
    import app
    from providers import ProviderError
    test_client, _ = client
    upload(test_client, make_pdf("Python developer"))

    def no_ai():
        raise ProviderError("Choose who scores the fit first: add an AI connection in Settings.")
    monkeypatch.setattr(app.connections, "active_provider", no_ai)

    answer = test_client.post("/api/cv/suggest")
    assert answer.status_code == 400 and "add an AI connection" in answer.get_json()["error"]


def test_filters_are_kept_for_next_time(client, monkeypatch):
    import app
    test_client, folder = client
    monkeypatch.setattr(app, "FILTERS_PATH", folder / "filters.json")
    assert test_client.get("/api/status").get_json()["filters"] is None
    test_client.post("/api/filters", json={"minFit": 40, "modes": ["hybrid", "remote"]})
    assert test_client.get("/api/status").get_json()["filters"] == {
        "minFit": 40, "modes": ["hybrid", "remote"]}
    assert test_client.post("/api/filters", json=[1, 2]).status_code == 400


# ---- Several CVs ----------------------------------------------------------------------

def review_for(cv, score):
    return {"cv": cv, "score": score, "scored": f"2026-11-0{score % 9 + 1} 10:00"}


def current_cv(test_client):
    return test_client.get("/api/status").get_json()["cv_id"]


def test_every_cv_you_upload_is_kept_in_your_list(client):
    test_client, _ = client
    upload(test_client, make_pdf("Python developer"), name="backend.pdf")
    upload(test_client, make_pdf("Machine learning engineer"), name="ai.pdf")

    names = [cv["name"] for cv in test_client.get("/api/status").get_json()["cvs"]]
    assert sorted(names) == ["ai.pdf", "backend.pdf"]


def test_switching_back_to_a_cv_brings_back_its_scores_and_years(client):
    test_client, folder = client
    upload(test_client, make_pdf("Python developer"), name="backend.pdf")
    backend = current_cv(test_client)
    test_client.post("/api/cv/years", json={"years": 2})
    upload(test_client, make_pdf("Machine learning engineer"), name="ai.pdf")
    ai = current_cv(test_client)
    # The job was scored for the backend CV, then again for the AI CV: the
    # backend review was moved to the earlier reviews.
    (folder / "fits.json").write_text(json.dumps({"job": review_for(ai, 40)}), encoding="utf-8")
    import earlier_reviews
    earlier_reviews.keep("job", review_for(backend, 70))

    answer = test_client.post("/api/cv/use", json={"id": backend})

    assert answer.get_json()["name"] == "backend.pdf"
    assert answer.get_json()["professional_years"] == 2
    assert current_cv(test_client) == backend
    fits = json.loads((folder / "fits.json").read_text(encoding="utf-8"))
    assert fits["job"]["score"] == 70
    assert [r["score"] for r in earlier_reviews.for_job("job", ai)] == [40]  # kept, not lost


def test_a_cv_removed_from_the_list_gets_its_scores_back_when_uploaded_again(client):
    test_client, folder = client
    upload(test_client, make_pdf("Python developer"), name="backend.pdf")
    backend = current_cv(test_client)
    upload(test_client, make_pdf("Machine learning engineer"), name="ai.pdf")
    import earlier_reviews
    earlier_reviews.keep("job", review_for(backend, 70))
    test_client.delete(f"/api/cv/{backend}")
    assert [cv["name"] for cv in test_client.get("/api/status").get_json()["cvs"]] == ["ai.pdf"]

    upload(test_client, make_pdf("Python developer"), name="backend.pdf")

    fits = json.loads((folder / "fits.json").read_text(encoding="utf-8"))
    assert fits["job"]["score"] == 70


def test_deleting_a_cv_with_its_scores_leaves_nothing_of_it(client, monkeypatch):
    test_client, folder = client
    upload(test_client, make_pdf("Python developer"), name="backend.pdf")
    backend = current_cv(test_client)
    (folder / "fits.json").write_text(json.dumps({"job": review_for(backend, 70)}), encoding="utf-8")
    import earlier_reviews
    earlier_reviews.keep("job", review_for(backend, 60))

    import migrations
    backup = folder / "backups" / "before-version-4"
    backup.mkdir(parents=True)
    (backup / "fits.json").write_text(json.dumps({"job": review_for(backend, 50),
                                                  "other": review_for("cccccccccccc", 30)}), encoding="utf-8")
    (backup / "cv_info.json").write_text(json.dumps({"name": "backend.pdf"}), encoding="utf-8")
    monkeypatch.setattr(migrations, "BACKUPS_DIR", folder / "backups")

    answer = test_client.delete(f"/api/cv/{backend}?scores=delete")

    assert answer.get_json()["cvs"] == []
    assert json.loads((folder / "fits.json").read_text(encoding="utf-8")) == {}
    assert earlier_reviews.for_job("job", backend) == []
    # Nor in the backups made before data upgrades: reviews quote the CV.
    assert list(json.loads((backup / "fits.json").read_text(encoding="utf-8"))) == ["other"]
    assert not (backup / "cv_info.json").exists()
    assert not (folder / "cv.txt").exists()   # it was the CV in use: none is loaded now
    assert test_client.get("/api/status").get_json()["cv"] is None


def test_no_switching_while_scoring(client, monkeypatch):
    import app
    test_client, _ = client
    upload(test_client, make_pdf("Python developer"))
    monkeypatch.setitem(app.fit_progress, "running", True)
    answer = test_client.post("/api/cv/use", json={"id": current_cv(test_client)})
    assert answer.status_code == 409


def test_an_unknown_cv_cannot_be_used_or_reach_other_folders(client):
    test_client, _ = client
    assert test_client.post("/api/cv/use", json={"id": "../../secret"}).status_code == 404
    assert test_client.delete("/api/cv/..secret").status_code == 404
    assert test_client.delete("/api/cv/..%2F..%2Fsecret").status_code >= 400  # never reaches the app
