"""DIA ASSIST — AI Health & Wellness Assistant.

Flask + SQLite + rule-based local AI. No external API keys required.
"""

import os
import secrets
import json
from datetime import datetime, date

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file, abort, g,
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from utils import report_parser, lab_analyzer, nutrition, skin_analyzer, ai_assistant, pdf_report, insights

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(UPLOAD_FOLDER, "reports")
SKIN_DIR = os.path.join(UPLOAD_FOLDER, "skin")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024
TRANSLATIONS_DIR = os.path.join(BASE_DIR, "translations")
SUPPORTED_LANGUAGES = ("en", "kn", "te", "hi")
LANGUAGE_LABELS = {"en": "English", "kn": "ಕನ್ನಡ", "te": "తెలుగు", "hi": "हिन्दी"}


def load_translations(language):
    language = language if language in SUPPORTED_LANGUAGES else "en"
    path = os.path.join(TRANSLATIONS_DIR, f"{language}.json")
    with open(path, "r", encoding="utf-8") as source:
        return json.load(source)


def current_language():
    language = session.get("language", "en")
    return language if language in SUPPORTED_LANGUAGES else "en"

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(SKIN_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["JSON_SORT_KEYS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


@app.before_request
def set_request_language():
    g.language = current_language()
    g.translations = load_translations(g.language)


@app.context_processor
def inject_translations():
    def translate(key, default=None):
        return g.translations.get(key, default if default is not None else key)
    return {
        "t": translate,
        "language": g.language,
        "languages": LANGUAGE_LABELS,
        "translations": g.translations,
        "english_translations": load_translations("en"),
    }

# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------
try:
    import sqlite3
    DB_PATH = os.path.join(BASE_DIR, "database.db")

    def get_db():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db():
        with get_db() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    age INTEGER,
                    sex TEXT,
                    report_date TEXT
                );
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER REFERENCES patients(id),
                    filename TEXT,
                    filepath TEXT,
                    report_type TEXT DEFAULT 'Other',
                    status TEXT DEFAULT 'STORED',
                    uploaded_at TEXT,
                    summary TEXT
                );
                CREATE TABLE IF NOT EXISTS lab_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER REFERENCES reports(id),
                    test TEXT,
                    value REAL,
                    value_text TEXT,
                    unit TEXT,
                    ref_low REAL,
                    ref_high REAL,
                    status TEXT
                );
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER REFERENCES reports(id),
                    session_token TEXT,
                    analysis_json TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(reports)").fetchall()}
            if "report_type" not in columns:
                conn.execute("ALTER TABLE reports ADD COLUMN report_type TEXT DEFAULT 'Other'")

    def save_analysis(report_path, filename, patient, analysis, report_type="Other"):
        token = secrets.token_urlsafe(16)
        now = datetime.now().isoformat()
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO patients (name, age, sex, report_date) VALUES (?, ?, ?, ?)",
                (patient.get("name"), patient.get("age"), patient.get("sex"), patient.get("date")),
            )
            patient_id = cur.lastrowid
            cur2 = conn.execute(
                "INSERT INTO reports (patient_id, filename, filepath, report_type, status, uploaded_at) VALUES (?,?,?,?,?,?)",
                (patient_id, filename, report_path, report_type, "ANALYZED", now),
            )
            report_id = cur2.lastrowid
            for a in analysis:
                conn.execute(
                    "INSERT INTO lab_results (report_id, test, value, value_text, unit, ref_low, ref_high, status) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (report_id, a.get("test"), a.get("value"),
                     str(a.get("value")), a.get("unit"),
                     a.get("ref_low"), a.get("ref_high"), a.get("status")),
                )
            import json
            conn.execute(
                "INSERT INTO analysis_sessions (report_id, session_token, analysis_json, created_at) "
                "VALUES (?,?,?,?)",
                (report_id, token, json.dumps(analysis), now),
            )
            conn.execute(
                "INSERT INTO activity_events (event_type, label, detail, created_at) VALUES (?,?,?,?)",
                ("report_analyzed", "Report analyzed", filename, now),
            )
            conn.execute(
                "INSERT INTO activity_events (event_type, label, detail, created_at) VALUES (?,?,?,?)",
                ("report_uploaded", "Report uploaded", filename, now),
            )
        session["session_token"] = token
        session["report_id"] = report_id
        session["patient"] = patient
        return token

    def load_session(token):
        import json
        with get_db() as conn:
            row = conn.execute(
                "SELECT asess.*, r.filename, r.report_type FROM analysis_sessions asess "
                "JOIN reports r ON r.id = asess.report_id WHERE asess.session_token = ?",
                (token,),
            ).fetchone()
            if not row:
                return None
            return {
                "token": row["session_token"],
                "analysis": json.loads(row["analysis_json"]),
                "filename": row["filename"],
                "report_type": row["report_type"],
            }

    def current_analysis():
        token = session.get("session_token")
        if not token:
            return None
        return load_session(token)

    def load_report_by_id(report_id):
        with get_db() as conn:
            row = conn.execute(
                "SELECT r.id, r.filename, r.report_type, r.uploaded_at, p.report_date, "
                "asess.analysis_json FROM reports r JOIN analysis_sessions asess ON asess.report_id = r.id "
                "JOIN patients p ON p.id = r.patient_id WHERE r.id = ?", (report_id,)
            ).fetchone()
        if not row:
            return None
        return {**dict(row), "analysis": json.loads(row["analysis_json"])}

    def clear_all_data():
        removed_files = []
        with get_db() as conn:
            conn.execute("DELETE FROM analysis_sessions")
            conn.execute("DELETE FROM lab_results")
            conn.execute("DELETE FROM reports")
            conn.execute("DELETE FROM patients")
            conn.execute("DELETE FROM activity_events")
        for sub in ("reports", "skin"):
            folder = os.path.join(UPLOAD_FOLDER, sub)
            if os.path.isdir(folder):
                for fname in os.listdir(folder):
                    if fname == ".gitkeep":
                        continue
                    fpath = os.path.join(folder, fname)
                    try:
                        os.remove(fpath)
                        removed_files.append(fpath)
                    except OSError:
                        pass
        session.clear()
        return removed_files

    def log_event(event_type, label, detail=""):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO activity_events (event_type, label, detail, created_at) VALUES (?,?,?,?)",
                (event_type, label, detail, datetime.now().isoformat()),
            )

    def load_report_history(limit=50):
        import json
        with get_db() as conn:
            rows = conn.execute(
                "SELECT r.id, r.filename, r.uploaded_at, p.report_date, p.name, "
                "asess.analysis_json FROM reports r JOIN patients p ON p.id = r.patient_id "
                "JOIN analysis_sessions asess ON asess.report_id = r.id "
                "ORDER BY r.id ASC LIMIT ?", (limit,)
            ).fetchall()
        return [{**dict(row), "analysis": json.loads(row["analysis_json"])} for row in rows]

    def load_timeline(limit=30):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT event_type, label, detail, created_at FROM activity_events "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

except ImportError as exc:  # pragma: no cover
    DB_PATH = None
    init_db, clear_all_data, current_analysis, load_report_by_id = None, None, None, None
    log_event, load_report_history, load_timeline = (lambda *a, **k: None,) * 3
    def no_import(*a, **k):
        return None
    save_analysis = no_import

init_db()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _patient_display(patient):
    p = patient or {}
    return {
        "name": p.get("name") or "Unknown",
        "age": p.get("age"),
        "sex": p.get("sex") or "Unknown",
        "date": p.get("date") or "Unknown",
    }


def _general_guidance(analysis):
    guidance = []
    if lab_analyzer.LabAnalyzer is None:  # pragma: no cover
        return guidance
    for a in analysis or []:
        key = a.get("key")
        if key in ("glucose", "fasting glucose", "hba1c") and a["status"] in ("HIGH", "BORDERLINE"):
            guidance += [
                "Reduce added sugar and sugary beverages.",
                "Choose high-fiber foods like vegetables, legumes and whole grains.",
                "Moderate refined carbohydrate portions.",
                "Select appropriate protein sources (lean poultry, fish, legumes, tofu).",
                "Maintain regular, moderate physical activity.",
                "Discuss your results with a healthcare professional.",
            ]
            break
    if any(a["status"] in ("HIGH", "BORDERLINE") for a in (analysis or [])
           if a["key"] in ("ldl", "total cholesterol", "triglycerides")):
        guidance += [
            "Emphasize fiber-rich foods, vegetables, fruits and whole grains.",
            "Moderate foods high in saturated and trans fats.",
            "Keep up regular physical activity.",
            "Discuss lipid management with your doctor.",
        ]
    if any(a["status"] in ("LOW", "BORDERLINE") for a in (analysis or [])
           if a["key"] == "vitamin d"):
        guidance.append(
            "Your Vitamin D result is below the report's reference range. Discuss appropriate "
            "management with your clinician (we do not prescribe supplements or doses)."
        )
    if not guidance:
        guidance = [
            "Maintain a balanced diet rich in vegetables, fruits and whole grains.",
            "Stay physically active most days of the week.",
            "Keep good sleep and hydration habits.",
            "Review your report with your doctor for personalized advice.",
        ]
    return guidance


def _diet_summary(analysis):
    return _general_guidance(analysis)


def _detect_report_type(filename, text):
    """Classify only when the uploaded filename or extracted text provides a signal."""
    haystack = f"{filename} {text[:5000]}".lower()
    if any(term in haystack for term in ("prescription", "rx", "dosage", "tablet", "capsule")):
        return "Prescription"
    if any(term in haystack for term in ("mri", "magnetic resonance", "ct scan", "computed tomography")):
        return "MRI/CT"
    if any(term in haystack for term in ("x-ray", "xray", "radiograph")):
        return "X-Ray"
    if any(term in haystack for term in ("scan", "ultrasound", "sonography")):
        return "Scan"
    if any(term in haystack for term in ("glucose", "hemoglobin", "cholesterol", "hba1c", "laboratory")):
        return "Blood Test"
    return "Other"

# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/set-language", methods=["POST"])
def set_language():
    selected = request.form.get("language", "en")
    if selected not in SUPPORTED_LANGUAGES:
        selected = "en"
    session["language"] = selected
    return redirect(request.form.get("next") or request.referrer or url_for("index"))


@app.route("/")
def index():
    session_data = current_analysis() if callable(current_analysis) else None
    return render_template("index.html", analysis_loaded=bool(session_data))


@app.route("/dashboard")
def dashboard():
    data = current_analysis() if callable(current_analysis) else None
    current_analysis_list = data["analysis"] if data else []
    intelligence = insights.build_intelligence(current_analysis_list, current_language())
    history = load_report_history() if callable(load_report_history) else []
    previous_analysis = history[-2]["analysis"] if len(history) > 1 else []
    changes = insights.compare_reports(previous_analysis, current_analysis_list)
    trends = insights.trend_series(history)
    timeline = load_timeline() if callable(load_timeline) else []
    recent_files = []
    if DB_PATH and os.path.exists(DB_PATH):
        import json
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT r.filename, r.uploaded_at, r.id, "
                    "(SELECT COUNT(*) FROM lab_results l WHERE l.report_id = r.id) as tests, "
                    "(SELECT COUNT(*) FROM lab_results l WHERE l.report_id = r.id AND l.status IN ('HIGH','LOW','BORDERLINE')) as abn "
                    "FROM reports r ORDER BY r.id DESC LIMIT 10"
                ).fetchall()
                recent_files = [dict(r) for r in rows]
        except sqlite3.Error:
            recent_files = []
    return render_template(
        "dashboard.html",
        analysis=data["analysis"] if data else None,
        patient=_patient_display(session.get("patient") or (data and {}) or None) if data else None,
        has_analysis=bool(data),
        recent_files=recent_files,
        intelligence=intelligence,
        trends=trends,
        timeline=timeline,
        report_count=len(history),
        changes=changes,
        extraction_confidence=session.get("extraction_confidence"),
        extraction_note=session.get("extraction_note"),
    )


@app.route("/reports")
def reports():
    return redirect(url_for("dashboard"))


@app.route("/health-analysis")
def health_analysis():
    return redirect(url_for("dashboard"))


@app.route("/ai-assistant")
def ai_assistant_page():
    return redirect(url_for("index"))


@app.route("/timeline")
def timeline_page():
    return redirect(url_for("trends"))


@app.route("/upload-report")
def upload_report():
    return render_template("report.html")


@app.route("/analyze-report", methods=["POST"])
def analyze_report():
    file = request.files.get("report")
    ok, err, ext = report_parser.validate_file(file)
    if not ok:
        flash(err, "error")
        return redirect(url_for("upload_report"))

    filename = report_parser.safe_filename(file.filename)
    dest = os.path.join(REPORTS_DIR, filename)
    file.save(dest)

    try:
        text, ocr_err = report_parser.extract_text(file, ext)
    except ValueError as exc:
        report_parser_safe_remove(dest)
        flash(str(exc), "error")
        return redirect(url_for("upload_report"))
    except Exception as exc:
        report_parser_safe_remove(dest)
        flash(f"Unexpected parsing error: {exc}", "error")
        return redirect(url_for("upload_report"))

    if not text.strip():
        report_parser_safe_remove(dest)
        msg = (ocr_err or "No readable text could be extracted from this file. "
                          "Please upload a clearer file (text PDF, DOCX, TXT, or a well-lit image).")
        flash(msg, "error")
        return redirect(url_for("upload_report"))
    if ocr_err:
        flash(f"Note: OCR partially unavailable ({ocr_err}). Text extraction may be limited.", "info")

    analyzer = lab_analyzer.LabAnalyzer(text)
    patient = analyzer.extract_patient()
    analysis = analyzer.analyze()
    report_type = _detect_report_type(filename, text)

    confidence = report_parser.estimate_confidence(text, analysis, ocr_err)
    session["extraction_confidence"] = confidence
    session["extraction_note"] = "Some values may need verification." if confidence < 85 else "Application estimate only; verify values against the source report."

    if not analysis:
        report_parser_safe_remove(dest)
        flash("No lab values were detected in this report. Please upload a report containing "
              "readable test results (e.g. glucose, cholesterol, HbA1c).", "error")
        return redirect(url_for("upload_report"))

    # rank abnormal first
    order = {"HIGH": 0, "LOW": 1, "BORDERLINE": 2, "NORMAL": 3, "UNKNOWN": 4}
    analysis.sort(key=lambda a: order.get(a["status"], 5))

    try:
        save_analysis(dest, filename, patient, analysis, report_type)
    except Exception as exc:
        report_parser_safe_remove(dest)
        flash(f"Could not store analysis results: {exc}", "error")
        return redirect(url_for("upload_report"))

    flash("Report analyzed successfully!", "success")
    return redirect(url_for("dashboard"))


def report_parser_safe_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


@app.route("/diet", methods=["GET", "POST"])
def diet():
    result = None
    errors = {}
    history = load_report_history() if callable(load_report_history) else []
    data = current_analysis() if callable(current_analysis) else None
    selected_report_id = request.form.get("report_id", type=int) if request.method == "POST" else None
    if selected_report_id and callable(load_report_by_id):
        data = load_report_by_id(selected_report_id)
    analysis = data["analysis"] if data else None

    if request.method == "POST":
        errors, kwargs = nutrition.validate_diet_form(request.form)
        if not selected_report_id or not data:
            errors["report_id"] = "Select an analyzed report before generating a report-informed plan."
            flash("Please upload and analyze a medical report, then select it for report-informed nutrition guidance.", "error")
        if errors:
            for field, msg in errors.items():
                flash(f"{msg}", "error")
        else:
            kwargs["analysis"] = analysis
            result = nutrition.generate_plan(**kwargs)
            selected_report_id = data.get("id") if data else None
            log_event("diet_plan", "Diet plan generated", f"Report {selected_report_id}" if selected_report_id else "No report selected")

    return render_template(
        "diet.html",
        result=result,
        errors=errors,
        form=request.form if request.method == "POST" else {},
        has_analysis=bool(data),
        reports=history,
        selected_report_id=selected_report_id or (data.get("id") if data else None),
        selected_report=data,
    )


@app.route("/upload-skin")
def upload_skin():
    result = session.get("skin_result")
    skin_path = session.get("skin_path")
    if result and skin_path and os.path.isfile(skin_path) and "image_data" not in result:
        from werkzeug.datastructures import FileStorage
        with open(skin_path, "rb") as source:
            restored = skin_analyzer.analyze_skin_image(
                FileStorage(stream=source, filename=os.path.basename(skin_path))
            )
        if "error" not in restored:
            result = restored
    return render_template("skin.html", result=result)


@app.route("/analyze-skin", methods=["POST"])
def analyze_skin():
    file = request.files.get("skin")
    ok, err, ext = report_parser.validate_file(file)
    if not ok:
        flash(err, "error")
        return redirect(url_for("upload_skin"))

    if ext not in ("jpg", "jpeg", "png"):
        flash("Skin analysis supports JPG, JPEG and PNG images only.", "error")
        return redirect(url_for("upload_skin"))

    filename = report_parser.safe_filename(file.filename)
    dest = os.path.join(SKIN_DIR, filename)
    file.save(dest)

    result = skin_analyzer.analyze_skin_image(file)
    if "error" in result:
        report_parser_safe_remove(dest)
        session.pop("skin_path", None)
        return render_template("skin.html", result=result)

    session["skin_path"] = dest
    session_result = dict(result)
    session_result.pop("image_data", None)
    session["skin_result"] = session_result
    session["skin_analyzed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_event("skin_analysis", "Skin analysis performed", filename)
    return render_template("skin.html", result=result)


@app.route("/delete-skin", methods=["POST"])
def delete_skin():
    path = session.pop("skin_path", None)
    session.pop("skin_result", None)
    if path:
        report_parser_safe_remove(path)
    flash("Skin image deleted from local storage.", "success")
    return redirect(url_for("upload_skin"))


@app.route("/skin-image")
def skin_image():
    path = session.get("skin_path")
    if not path or not os.path.isfile(path):
        abort(404)
    return send_file(path)


@app.route("/chat", methods=["POST"])
def chat():
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}
    question = (payload.get("message") or "").strip()

    data = current_analysis() if callable(current_analysis) else None
    analysis = data["analysis"] if data else None
    patient = session.get("patient") if isinstance(session.get("patient"), dict) else {}

    requested_language = payload.get("language")
    language = requested_language if requested_language in SUPPORTED_LANGUAGES else current_language()
    answer = ai_assistant.chat_response(
        question, analysis=analysis, patient=patient,
        language=language, skin_context=session.get("skin_result"),
    )
    return jsonify({"reply": answer})


@app.route("/trends")
def trends():
    history = load_report_history() if callable(load_report_history) else []
    return render_template("trends.html", trends=insights.trend_series(history), report_count=len(history))


@app.route("/privacy")
def privacy():
    reports = load_report_history() if callable(load_report_history) else []
    skin_count = 0
    if os.path.isdir(SKIN_DIR):
        skin_count = sum(1 for name in os.listdir(SKIN_DIR) if name != ".gitkeep")
    with get_db() as conn:
        sessions = conn.execute("SELECT COUNT(*) FROM analysis_sessions").fetchone()[0]
    return render_template(
        "privacy.html", report_count=len(reports), skin_count=skin_count,
        session_count=sessions, storage_path=UPLOAD_FOLDER,
    )


@app.route("/download-report", methods=["GET", "POST"])
def download_report():
    data = current_analysis() if callable(current_analysis) else None
    if not data:
        flash("No analysis available to generate a PDF. Analyze a medical report first.", "error")
        return redirect(url_for("upload_report"))

    patient = _patient_display(session.get("patient") or {})
    report_date = date.today().strftime("%d %B %Y")
    extra = {
        "general_notes": insights.build_intelligence(data["analysis"], current_language())["insights"]["next_steps"],
        "diet_summary": insights.diet_guidance(data["analysis"], current_language()),
        "intelligence": insights.build_intelligence(data["analysis"], current_language()),
        "trends": insights.trend_series(load_report_history() if callable(load_report_history) else []),
        "language": current_language(),
    }
    try:
        pdf_bytes = pdf_report.generate_pdf(patient, data["analysis"], report_date, extra=extra)
        log_event("pdf_generated", "PDF report generated", filename if (filename := data.get("filename")) else "")
    except Exception as exc:
        flash(f"PDF generation failed: {exc}", "error")
        return redirect(url_for("dashboard"))

    filename = f"dia_assist_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    from io import BytesIO
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/delete-data", methods=["POST"])
def delete_data():
    try:
        removed = clear_all_data()
        flash(f"All your data has been deleted ({len(removed)} files removed).", "success")
    except Exception as exc:
        flash(f"Could not fully delete data: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("404.html", message="A server error occurred. Please try again."), 500


@app.errorhandler(RequestEntityTooLarge)
def too_large(e):
    flash("File too large. Maximum allowed size is 10 MB.", "error")
    return redirect(url_for("upload_report"))


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  DIA ASSIST — AI Health & Wellness Assistant")
    print(f"  Open in Chrome:  http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(debug=False, host="127.0.0.1", port=5000)