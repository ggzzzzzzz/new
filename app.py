import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from typing import List, Optional, Dict, Any

from flask import Flask, render_template, request, redirect, url_for, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import pandas as pd
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "words.db"
DICTIONARY_DB_PATH = BASE_DIR / "stardict.db"


load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "SQLALCHEMY_DATABASE_URI", f"sqlite:///{DEFAULT_DB_PATH}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Exposed for advanced users; current implementation uses simplified FSRS-like logic
app.config["FSRS_WEIGHTS"] = {
    "enable_sm2_style": True,
}

db = SQLAlchemy(app)


class Word(db.Model):
    __tablename__ = "word"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    meaning = db.Column(db.Text, nullable=False)
    example_sentence = db.Column(db.Text)
    part_of_speech = db.Column(db.String(50))
    difficulty_level = db.Column(db.String(20), default="medium")
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    times_studied = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)
    last_studied = db.Column(db.DateTime)
    next_review = db.Column(db.DateTime)
    ease_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=0)
    repetitions = db.Column(db.Integer, default=0)


class StudyPlan(db.Model):
    __tablename__ = "study_plan"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    words_per_day = db.Column(db.Integer, default=20)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class StudySession(db.Model):
    __tablename__ = "study_session"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word_id = db.Column(db.Integer, nullable=False)
    quality = db.Column(db.Integer, nullable=False)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)
    next_review = db.Column(db.DateTime)
    ease_factor = db.Column(db.Float)
    interval = db.Column(db.Integer)


def get_active_study_plan(db_session) -> StudyPlan:
    plan = db_session.query(StudyPlan).filter_by(is_active=True).order_by(StudyPlan.id.desc()).first()
    if plan is None:
        plan = StudyPlan(words_per_day=20, is_active=True)
        db_session.add(plan)
        db_session.commit()
    return plan


def current_time() -> datetime:
    return datetime.now(timezone.utc)


def to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def lookup_dictionary_entry(query_word: str) -> Optional[Dict[str, Any]]:
    if not DICTIONARY_DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DICTIONARY_DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT word, phonetic, definition, pos, detail FROM stardict WHERE word = ? COLLATE NOCASE LIMIT 1",
            (query_word,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "word": row["word"],
            "phonetic": row["phonetic"],
            "definition": row["definition"],
            "pos": row["pos"],
            "detail": row["detail"],
        }
    except Exception:
        return None


def fsrs_update_schedule(existing_word: Word, quality: int, review_moment: Optional[datetime] = None) -> None:
    """Update the scheduling fields for a word using a simplified FSRS/SM-2 style algorithm.

    Quality: 0-5 scale. Values < 3 are treated as a lapse; values >= 3 are treated as success.
    """
    if review_moment is None:
        review_moment = current_time()

    # Normalize timestamps to naive UTC for SQLite
    review_moment = to_naive_utc(review_moment)

    minimum_ease = 1.3
    ease_factor = existing_word.ease_factor or 2.5
    interval_days = existing_word.interval or 0
    repetitions = existing_word.repetitions or 0

    if quality < 3:
        repetitions = 0
        interval_days = 1
        ease_factor = max(minimum_ease, ease_factor - 0.2)
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = int(round(interval_days * ease_factor))

        ease_delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        ease_factor = max(minimum_ease, ease_factor + ease_delta)
        repetitions = repetitions + 1

    next_review = review_moment + timedelta(days=interval_days)

    existing_word.ease_factor = float(ease_factor)
    existing_word.interval = int(interval_days)
    existing_word.repetitions = int(repetitions)
    existing_word.last_studied = review_moment
    existing_word.next_review = next_review
    existing_word.times_studied = (existing_word.times_studied or 0) + 1
    if quality >= 3:
        existing_word.times_correct = (existing_word.times_correct or 0) + 1


def get_due_or_new_word(db_session) -> Optional[Word]:
    plan = get_active_study_plan(db_session)

    now = to_naive_utc(current_time())

    due_word = (
        db_session.query(Word)
        .filter((Word.next_review == None) | (Word.next_review <= now))
        .order_by(
            # Prioritize those with a scheduled next_review that is already due
            func.coalesce(Word.next_review, datetime(1970, 1, 1)),
            Word.repetitions.asc(),
            Word.date_added.asc(),
        )
        .first()
    )
    if due_word is not None:
        return due_word

    today_begin = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    studied_today = (
        db_session.query(StudySession)
        .filter(StudySession.review_date >= today_begin)
        .count()
    )

    if studied_today >= plan.words_per_day:
        return None

    new_word = (
        db_session.query(Word)
        .filter(Word.repetitions == 0)
        .order_by(Word.date_added.asc())
        .first()
    )
    return new_word


def calculate_summary_stats(db_session) -> Dict[str, Any]:
    total_words = db_session.query(Word).count()

    now = to_naive_utc(current_time())
    due_count = (
        db_session.query(Word)
        .filter((Word.next_review == None) | (Word.next_review <= now))
        .count()
    )

    today_begin = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sessions_today = (
        db_session.query(StudySession).filter(StudySession.review_date >= today_begin).all()
    )

    studied_today = len(sessions_today)
    if studied_today > 0:
        avg_quality = sum(s.quality for s in sessions_today) / studied_today
    else:
        avg_quality = 0.0

    correct_total = db_session.query(func.coalesce(func.sum(Word.times_correct), 0)).scalar() or 0
    studied_total = db_session.query(func.coalesce(func.sum(Word.times_studied), 0)).scalar() or 0
    accuracy = (correct_total / studied_total) * 100.0 if studied_total else 0.0

    return {
        "total_words": total_words,
        "due_count": due_count,
        "studied_today": studied_today,
        "avg_quality_today": round(avg_quality, 2),
        "accuracy": round(accuracy, 2),
    }


with app.app_context():
    db.create_all()
    get_active_study_plan(db.session)


@app.route("/")
def index():
    stats = calculate_summary_stats(db.session)
    plan = get_active_study_plan(db.session)
    return render_template("index.html", stats=stats, plan=plan)


@app.route("/words")
def words_list():
    query = request.args.get("q", "").strip()
    q = db.session.query(Word)
    if query:
        like = f"%{query}%"
        q = q.filter((Word.word.ilike(like)) | (Word.meaning.ilike(like)))
    words = q.order_by(Word.word.asc()).all()
    return render_template("words.html", words=words, query=query)


@app.route("/add", methods=["GET", "POST"])
def add_word():
    if request.method == "POST":
        word_str = request.form.get("word", "").strip()
        meaning = request.form.get("meaning", "").strip()
        example = request.form.get("example_sentence", "").strip()
        pos = request.form.get("part_of_speech", "").strip()
        difficulty = request.form.get("difficulty_level", "medium").strip() or "medium"

        if not word_str:
            return render_template("add_word.html", error="Word is required", suggest=None)

        if not meaning:
            dict_entry = lookup_dictionary_entry(word_str)
            if dict_entry and dict_entry.get("definition"):
                meaning = dict_entry.get("definition")

        new_w = Word(
            word=word_str,
            meaning=meaning or "",
            example_sentence=example or None,
            part_of_speech=pos or None,
            difficulty_level=difficulty,
        )
        db.session.add(new_w)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return render_template("add_word.html", error="Word already exists", suggest=None)

        return redirect(url_for("words_list"))

    # GET suggests dictionary lookup
    query_word = request.args.get("word", "").strip()
    suggest = lookup_dictionary_entry(query_word) if query_word else None
    return render_template("add_word.html", suggest=suggest, error=None)


@app.route("/edit/<int:word_id>", methods=["GET", "POST"])
def edit_word(word_id: int):
    w = db.session.get(Word, word_id)
    if not w:
        return redirect(url_for("words_list"))

    if request.method == "POST":
        w.word = request.form.get("word", w.word).strip()
        w.meaning = request.form.get("meaning", w.meaning).strip()
        w.example_sentence = request.form.get("example_sentence", w.example_sentence)
        w.part_of_speech = request.form.get("part_of_speech", w.part_of_speech)
        w.difficulty_level = request.form.get("difficulty_level", w.difficulty_level) or "medium"
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return render_template("edit_word.html", word=w, error="Word already exists")
        return redirect(url_for("words_list"))

    return render_template("edit_word.html", word=w, error=None)


@app.route("/delete/<int:word_id>", methods=["POST"])
def delete_word(word_id: int):
    w = db.session.get(Word, word_id)
    if w:
        db.session.delete(w)
        db.session.commit()
    return redirect(url_for("words_list"))


@app.route("/delete_bulk", methods=["POST"])
def delete_bulk_words():
    ids = request.form.getlist("ids")
    if not ids:
        return redirect(url_for("words_list"))
    try:
        id_ints = [int(x) for x in ids if str(x).strip().isdigit()]
    except Exception:
        id_ints = []
    if not id_ints:
        return redirect(url_for("words_list"))

    # Remove related study sessions first, then words
    db.session.query(StudySession).filter(StudySession.word_id.in_(id_ints)).delete(synchronize_session=False)
    db.session.query(Word).filter(Word.id.in_(id_ints)).delete(synchronize_session=False)
    db.session.commit()
    return redirect(url_for("words_list"))


@app.route("/delete_all", methods=["POST"])
def delete_all_words():
    # Remove all study sessions and words
    db.session.query(StudySession).delete()
    db.session.query(Word).delete()
    db.session.commit()
    return redirect(url_for("words_list"))


@app.route("/import", methods=["GET", "POST"])
def import_csv():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return render_template("import_csv.html", error="Please upload a CSV file", result=None)

        try:
            df = pd.read_csv(file)
        except Exception:
            return render_template("import_csv.html", error="Failed to read CSV. Ensure it's a valid CSV.", result=None)

        normalized_cols = [c.strip().lower() for c in df.columns]
        df.columns = normalized_cols

        imported_count = 0
        updated_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            word_str = str(row.get("word", "")).strip()
            if not word_str or word_str.lower() == "nan":
                skipped_count += 1
                continue

            meaning = row.get("meaning")
            example = row.get("example_sentence")
            part_of_speech = row.get("part_of_speech")
            difficulty_level = row.get("difficulty_level", "medium") or "medium"

            if (meaning is None or str(meaning).strip() == ""):
                dict_entry = lookup_dictionary_entry(word_str)
                if dict_entry and dict_entry.get("definition"):
                    meaning = dict_entry.get("definition")
                else:
                    meaning = ""

            existing = db.session.query(Word).filter_by(word=word_str).first()
            if existing:
                existing.meaning = str(meaning) if meaning is not None else existing.meaning
                if example and str(example).strip():
                    existing.example_sentence = str(example)
                if part_of_speech and str(part_of_speech).strip():
                    existing.part_of_speech = str(part_of_speech)
                existing.difficulty_level = str(difficulty_level)
                updated_count += 1
            else:
                new_word = Word(
                    word=word_str,
                    meaning=str(meaning) if meaning is not None else "",
                    example_sentence=str(example) if example and str(example).strip() else None,
                    part_of_speech=str(part_of_speech) if part_of_speech and str(part_of_speech).strip() else None,
                    difficulty_level=str(difficulty_level),
                )
                db.session.add(new_word)
                imported_count += 1

        db.session.commit()

        result = {
            "imported": imported_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "total": int(imported_count + updated_count + skipped_count),
        }
        return render_template("import_csv.html", error=None, result=result)

    return render_template("import_csv.html", error=None, result=None)


@app.route("/export/csv")
def export_csv():
    words = db.session.query(Word).order_by(Word.word.asc()).all()
    rows = []
    for w in words:
        rows.append({
            "word": w.word,
            "meaning": w.meaning,
            "example_sentence": w.example_sentence or "",
            "part_of_speech": w.part_of_speech or "",
            "difficulty_level": w.difficulty_level or "",
            "date_added": w.date_added.isoformat() if w.date_added else "",
            "times_studied": w.times_studied or 0,
            "times_correct": w.times_correct or 0,
            "last_studied": w.last_studied.isoformat() if w.last_studied else "",
            "next_review": w.next_review.isoformat() if w.next_review else "",
            "ease_factor": w.ease_factor or 2.5,
            "interval": w.interval or 0,
            "repetitions": w.repetitions or 0,
        })

    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=words_export.csv"
        },
    )


@app.route("/export/anki")
def export_anki():
    words = db.session.query(Word).order_by(Word.word.asc()).all()
    lines = []
    for w in words:
        back_parts: List[str] = []
        if w.meaning:
            back_parts.append(w.meaning)
        if w.part_of_speech:
            back_parts.append(f"({w.part_of_speech})")
        if w.example_sentence:
            back_parts.append(f"Example: {w.example_sentence}")
        back_text = " — ".join([p for p in back_parts if p])
        lines.append(f"{w.word}\t{back_text}")

    content = "\n".join(lines).encode("utf-8")
    return Response(
        content,
        mimetype="text/tab-separated-values",
        headers={
            "Content-Disposition": "attachment; filename=anki_export.txt"
        },
    )


@app.route("/study")
def study():
    w = get_due_or_new_word(db.session)
    plan = get_active_study_plan(db.session)
    stats = calculate_summary_stats(db.session)
    return render_template("study.html", word=w, plan=plan, stats=stats)


@app.route("/study/rate", methods=["POST"])
def study_rate():
    word_id = request.form.get("word_id")
    quality_str = request.form.get("quality")

    if not word_id or not quality_str:
        return redirect(url_for("study"))

    w = db.session.get(Word, int(word_id))
    if not w:
        return redirect(url_for("study"))

    try:
        quality = int(quality_str)
    except ValueError:
        quality = 0

    fsrs_update_schedule(w, quality)
    session = StudySession(
        word_id=w.id,
        quality=quality,
        review_date=to_naive_utc(current_time()),
        next_review=w.next_review,
        ease_factor=w.ease_factor,
        interval=w.interval,
    )
    db.session.add(session)
    db.session.commit()

    return redirect(url_for("study"))


@app.route("/study_plan", methods=["GET", "POST"])
def study_plan():
    plan = get_active_study_plan(db.session)
    if request.method == "POST":
        try:
            words_per_day = int(request.form.get("words_per_day", plan.words_per_day))
            if words_per_day < 1:
                words_per_day = 1
        except ValueError:
            words_per_day = plan.words_per_day

        plan.words_per_day = words_per_day
        db.session.commit()
        return redirect(url_for("study"))

    return render_template("study_plan.html", plan=plan)


@app.route("/progress")
def progress():
    stats = calculate_summary_stats(db.session)

    # Aggregate recent sessions for a simple activity display
    last_30_days = datetime.utcnow() - timedelta(days=30)
    sessions = (
        db.session.query(StudySession)
        .filter(StudySession.review_date >= last_30_days)
        .order_by(StudySession.review_date.desc())
        .limit(100)
        .all()
    )

    return render_template("progress.html", stats=stats, sessions=sessions)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)