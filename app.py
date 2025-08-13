import argparse
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def get_database_uri() -> str:
    base_dir = Path(__file__).resolve().parent
    db_path = os.environ.get("DATABASE_PATH", str(base_dir / "words.db"))
    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    database_uri = os.environ.get("SQLALCHEMY_DATABASE_URI", get_database_uri())
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    engine_options = {"pool_pre_ping": True}
    if database_uri.startswith("sqlite:///"):
        engine_options["connect_args"] = {"check_same_thread": False}
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    db.init_app(app)

    register_health_endpoint(app)

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        ensure_initial_study_plan()

    return app


class Word(db.Model):
    __tablename__ = "word"

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    meaning = db.Column(db.Text, nullable=False, default="")
    example_sentence = db.Column(db.Text)
    part_of_speech = db.Column(db.String(50))
    difficulty_level = db.Column(db.String(20), nullable=False, default="medium")
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    times_studied = db.Column(db.Integer, nullable=False, default=0)
    times_correct = db.Column(db.Integer, nullable=False, default=0)
    last_studied = db.Column(db.DateTime)
    next_review = db.Column(db.DateTime)
    ease_factor = db.Column(db.Float, nullable=False, default=2.5)
    interval = db.Column(db.Integer, nullable=False, default=0)
    repetitions = db.Column(db.Integer, nullable=False, default=0)

    study_sessions = db.relationship("StudySession", back_populates="word_ref", cascade="all, delete-orphan")


class StudyPlan(db.Model):
    __tablename__ = "study_plan"

    id = db.Column(db.Integer, primary_key=True)
    words_per_day = db.Column(db.Integer, nullable=False, default=20)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class StudySession(db.Model):
    __tablename__ = "study_session"

    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey("word.id"), nullable=False)
    quality = db.Column(db.Integer, nullable=False)  # 0-5
    review_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    next_review = db.Column(db.DateTime)
    ease_factor = db.Column(db.Float)
    interval = db.Column(db.Integer)

    word_ref = db.relationship("Word", back_populates="study_sessions")


def ensure_initial_study_plan() -> None:
    if StudyPlan.query.count() == 0:
        plan = StudyPlan(words_per_day=20, is_active=True)
        db.session.add(plan)
        db.session.commit()


def register_health_endpoint(app: Flask) -> None:
    @app.get("/healthz")
    def healthz():
        try:
            # Simple DB roundtrip
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "database": "connected"})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "error", "database": str(exc)}), 500


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="English Words Memorizer - App and DB utilities")
    parser.add_argument("--init-db", action="store_true", help="Initialize the database and exit")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)

    args = parser.parse_args()

    app = create_app()

    if args.init_db:
        # Tables are created in create_app; just verify a simple roundtrip here
        with app.app_context():
            db.session.execute(db.text("SELECT 1"))
        print("Database initialized and verified.")
    else:
        app.run(host=args.host, port=args.port, debug=True)