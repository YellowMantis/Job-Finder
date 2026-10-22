"""Tests for scoring jobs: the shared code in scoring.py, and the scoring run
(score_jobs in app.py). A fake provider stands in for the AI, so no Claude
session or model is started and no tokens are used."""

import json

import pytest

import scoring
from providers import Provider, ProviderError

CV = "B.Sc. in Computer Science. Wrote Python automation on Linux."


def review(job_id, **changes):
    """One review in the shape the AI must answer with."""
    return {"job_id": job_id, "years_required": 0, "work_mode": "hybrid", "summary": "ok",
            "defence_related": False,
            "requirements": [
                {"requirement": "Python", "importance": "core", "evidence": "Python automation",
                 "match": "yes"},
                {"requirement": "Linux", "importance": "must", "evidence": "on Linux",
                 "match": "yes"}],
            **changes}


class FakeProvider(Provider):
    """Answers every request with the next of the given answers, and remembers
    what it was asked."""
    id = "fake"
    label = "a fake AI"
    reviewer_prefix = "Fake"
    batch_size = 10

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def ask(self, system_prompt, prompt, schema):
        self.prompts.append(prompt)
        answer = self.answers.pop(0)
        if callable(answer):  # lets a test act while a request is "running"
            answer = answer(prompt)
        return answer, {"model": "fake-1", "input_tokens": 100, "output_tokens": 50, "seconds": 1}


def jobs(count):
    return [{"url": f"job-{n}", "title": f"Engineer {n}", "company": "Acme",
             "text": f"Posting {n}", "has_text": True, "fit": None,
             "hidden": None} for n in range(count)]


@pytest.fixture(autouse=True)
def log_in_temp_folder(tmp_path, monkeypatch):
    """Every test here writes its scoring log to a throwaway folder."""
    monkeypatch.setattr(scoring, "SCORING_LOG_PATH", tmp_path / "scoring_log.json")
    monkeypatch.setattr(scoring, "DATA_DIR", tmp_path)
    return tmp_path


# ---- scoring.py: the part every provider shares ----------------------------------------

def test_reviews_are_matched_to_their_jobs_and_scored():
    provider = FakeProvider({"reviews": [review(2), review(1, summary="first")]})
    result = scoring.review_batch(provider, CV, 1, jobs(2))
    assert set(result) == {"job-0", "job-1"}
    assert result["job-0"]["summary"] == "first"
    assert result["job-0"]["score"] == 100
    assert result["job-0"]["model"] == "Fake (fake-1)"   # signed by the provider


def test_the_prompt_numbers_every_posting():
    provider = FakeProvider({"reviews": []})
    scoring.review_batch(provider, CV, 1, jobs(2))
    assert "=== JOB 1: Engineer 0 at Acme ===" in provider.prompts[0]
    assert "=== JOB 2: Engineer 1 at Acme ===" in provider.prompts[0]


def test_a_review_for_a_job_never_sent_is_ignored():
    provider = FakeProvider({"reviews": [review(1), review(7)]})
    assert set(scoring.review_batch(provider, CV, 1, jobs(2))) == {"job-0"}


def test_an_answer_given_as_json_text_is_accepted():
    provider = FakeProvider(json.dumps({"reviews": [review(1)]}))
    assert "job-0" in scoring.review_batch(provider, CV, 1, jobs(1))


def test_a_malformed_answer_is_asked_for_once_more():
    provider = FakeProvider({"reviews": "not a list"}, {"reviews": [review(1)]})
    assert "job-0" in scoring.review_batch(provider, CV, 1, jobs(1))
    assert len(provider.prompts) == 2


def test_two_malformed_answers_give_a_plain_error():
    provider = FakeProvider({"oops": 1}, {"oops": 2})
    with pytest.raises(ProviderError, match="wrong shape twice"):
        scoring.review_batch(provider, CV, 1, jobs(1))


def test_every_request_is_logged_even_a_failed_one(log_in_temp_folder):
    provider = FakeProvider({"oops": 1}, {"reviews": [review(1)]})
    scoring.review_batch(provider, CV, 1, jobs(1))
    log = json.loads((log_in_temp_folder / "scoring_log.json").read_text(encoding="utf-8"))
    assert len(log) == 2
    assert log[0]["provider"] == "fake" and log[0]["input_tokens"] == 100
    assert log[0]["cache_read_tokens"] == 0   # not reported by this provider: counted as 0


def test_years_of_experience_are_read_from_the_cv():
    assert scoring.read_cv_facts(FakeProvider({"professional_years": 1}), CV) == \
        {"professional_years": 1}


# ---- app.score_jobs: the run in the background --------------------------------------

@pytest.fixture
def app_with(tmp_path, monkeypatch):
    """Returns a function that sets up the app with a given provider and 25 jobs."""
    import app

    (tmp_path / "cv.txt").write_text(CV, encoding="utf-8")
    (tmp_path / "cv_info.json").write_text('{"professional_years": 1}', encoding="utf-8")
    monkeypatch.setattr(app, "CV_TEXT_PATH", tmp_path / "cv.txt")
    monkeypatch.setattr(app, "CV_INFO_PATH", tmp_path / "cv_info.json")
    monkeypatch.setattr(app, "FITS_PATH", tmp_path / "fits.json")
    monkeypatch.setattr(app, "DATA_DIR", tmp_path)
    monkeypatch.setattr(app, "jobs_for_display", lambda cv: jobs(25))

    def setup(provider):
        monkeypatch.setattr(app.connections, "active_provider", lambda: provider)
        app.fit_progress.update(running=True, done=0, total=0, error="", stop_requested=False)
        return app
    return setup


def answer_all(prompt):
    """A review for every job in the prompt."""
    return {"reviews": [review(n) for n in range(1, prompt.count("=== JOB") + 1)]}


def test_jobs_are_scored_in_batches_of_the_providers_size(app_with):
    provider = FakeProvider(answer_all, answer_all, answer_all)
    app = app_with(provider)
    app.score_jobs({f"job-{n}" for n in range(25)})
    assert [p.count("=== JOB") for p in provider.prompts] == [10, 10, 5]
    assert app.fit_progress["done"] == 25 and app.fit_progress["running"] is False


def test_stop_finishes_the_current_batch_and_starts_no_other(app_with):
    def press_stop_then_answer(prompt):
        app.fit_progress["stop_requested"] = True  # as if you pressed Stop now
        return answer_all(prompt)

    provider = FakeProvider(press_stop_then_answer, answer_all, answer_all)
    app = app_with(provider)
    app.score_jobs({f"job-{n}" for n in range(25)})
    assert len(provider.prompts) == 1       # the batch under way was finished and kept
    assert app.fit_progress["done"] == 10


def test_only_the_jobs_asked_for_are_scored(app_with):
    provider = FakeProvider(answer_all)
    app = app_with(provider)
    app.score_jobs({"job-1", "job-2", "job-3"})
    assert provider.prompts[0].count("=== JOB") == 3


def test_a_provider_that_cant_be_used_explains_why_on_the_page(app_with):
    class Unavailable(FakeProvider):
        def ask(self, system_prompt, prompt, schema):
            raise ProviderError("Ollama is not running. Start Ollama and try again.")

    app = app_with(Unavailable())
    app.score_jobs({"job-1"})
    assert app.fit_progress["error"] == "Ollama is not running. Start Ollama and try again."
    assert app.fit_progress["running"] is False


def test_scoring_again_redoes_jobs_that_have_a_score(app_with, monkeypatch):
    import app
    provider = FakeProvider(answer_all)
    application = app_with(provider)
    scored = [{**job, "fit": {"score": 40}} for job in jobs(3)]
    monkeypatch.setattr(app, "jobs_for_display", lambda cv: scored)

    application.score_jobs({"job-0", "job-1"}, again=True)
    assert provider.prompts[0].count("=== JOB") == 2


def test_jobs_with_a_score_are_skipped_unless_asked_again(app_with, monkeypatch):
    import app
    provider = FakeProvider(answer_all)
    application = app_with(provider)
    monkeypatch.setattr(app, "jobs_for_display", lambda cv: [{**job, "fit": {"score": 40}}
                                                            for job in jobs(3)])
    application.score_jobs({"job-0", "job-1"})
    assert provider.prompts == []          # nothing asked: both already scored


def test_an_api_runs_several_batches_at_once_and_scores_them_all(app_with):
    import threading
    import time
    running, most = [0], [0]
    lock = threading.Lock()

    def slow_answer(prompt):
        with lock:
            running[0] += 1
            most[0] = max(most[0], running[0])
        time.sleep(0.1)
        with lock:
            running[0] -= 1
        return answer_all(prompt)

    provider = FakeProvider(*[slow_answer] * 3)
    provider.requests_at_once = 3
    app = app_with(provider)
    app.score_jobs({f"job-{n}" for n in range(25)})

    assert most[0] > 1                      # batches overlapped
    assert app.fit_progress["done"] == 25   # and every job was scored once
    assert app.fit_progress["error"] == ""
