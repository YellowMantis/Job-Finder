"""Your saved CVs, so you can switch between them without uploading again.

Each CV you upload is kept in its own folder, named by its fingerprint (the
same one its fit reviews carry, see app.cv_id):

  data/cvs/<fingerprint>/cv.pdf     the file you uploaded
  data/cvs/<fingerprint>/cv.txt     its text
  data/cvs/<fingerprint>/info.json  its name, upload time and years of paid work

The CV in use is also kept where it always was (data/cv.pdf, cv.txt and
cv_info.json), so the rest of the app reads it as before; switching CV copies
the chosen one there.

Removing a CV from the list deletes its folder but keeps its fit reviews:
upload the same CV again and its scores are back. Deleting it with its
reviews is a separate choice (app.py, earlier_reviews.forget).
"""

import json
import shutil

from settings import DATA_DIR

CVS_DIR = DATA_DIR / "cvs"


def _folder(cv):
    # A fingerprint is 12 hex characters; anything else never names a folder.
    if not (isinstance(cv, str) and len(cv) == 12 and all(c in "0123456789abcdef" for c in cv)):
        raise KeyError(cv)
    return CVS_DIR / cv


def add(cv, pdf_path, text, info):
    """Keep a CV in the list (or update it, if it is already there)."""
    folder = _folder(cv)
    folder.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        shutil.copyfile(pdf_path, folder / "cv.pdf")
    (folder / "cv.txt").write_text(text, encoding="utf-8")
    save_info(cv, info)


def save_info(cv, info):
    folder = _folder(cv)
    if folder.exists():
        (folder / "info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False),
                                          encoding="utf-8")


def info(cv):
    """The saved details of a CV in the list, or None if it isn't there."""
    path = _folder(cv) / "info.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def listing():
    """Every saved CV, the most recently uploaded first: [{"id", "name", "uploaded"}]."""
    if not CVS_DIR.exists():
        return []
    saved = []
    for folder in CVS_DIR.iterdir():
        details = info(folder.name) if folder.is_dir() and len(folder.name) == 12 else None
        if details:
            saved.append({"id": folder.name, "name": details.get("name", "CV"),
                          "uploaded": details.get("uploaded", "")})
    return sorted(saved, key=lambda cv: cv["uploaded"], reverse=True)


def files(cv):
    """The PDF and text file of a saved CV, or None if it isn't in the list."""
    folder = _folder(cv)
    if not (folder / "cv.txt").exists():
        return None
    return folder / "cv.pdf", folder / "cv.txt"


def remove(cv):
    """Take a CV off the list. Its fit reviews are kept."""
    shutil.rmtree(_folder(cv), ignore_errors=True)
