# DIA ASSIST – AI Health & Wellness Assistant

A full-stack **Flask** web application that acts as a local, privacy-first **AI health & wellness assistant**. It analyzes uploaded medical reports (PDF/DOC/DOCX/TXT/images via OCR), generates AI-style health insights using a **rule-based local engine (no API key required)**, creates personalized sample diet plans, performs basic skin-image analysis, provides a chatbot ("Ask Dia"), and produces **downloadable PDF health reports**.

> **IMPORTANT DISCLAIMER:** This project is a prototype for educational/demonstration purposes only. It does **not** provide medical diagnosis, treatment, or professional medical advice. Always consult a qualified healthcare professional.

---

## Features

- 📁 **Medical Report Analyzer** – Upload PDF, DOCX, DOC, TXT, JPG, JPEG, PNG; extract lab values with strong regex patterns; OCR fallback for scanned PDFs/images
- 🧪 **Lab Analysis Engine** – Flags results as HIGH / LOW / BORDERLINE / NORMAL / UNKNOWN using the report's own reference ranges when available
- 📊 **Result Dashboard** – Patient overview, key findings, abnormal results, full test table, explanations, lifestyle guidance, Chart.js graphs
- 🥗 **AI Diet Planner** – Mifflin-St Jeor BMR/calorie estimation, goal-adjusted macros, sample meal plan (B/L/Snacks/Dinner), allergy-aware & report-adaptive
- 🧴 **Skin AI (visual preview)** – Face image upload, rule-based assessment of visible concerns with severity and skincare routines
- 💬 **Ask Dia Chatbot** – Floating chat widget that answers questions about the analyzed report and general wellness (local rule-based engine)
- 📄 **PDF Health Report** – Professional, printable medical-style PDF generated with ReportLab
- 🌙 **Premium SaaS UI** – Glass/soft cards, gradients, dark mode toggle, sidebar + topbar, sidebars, toasts, drag-and-drop upload, loading animations, responsive
- 🔒 **Privacy-first** – Uploads stored in private directories, never served publicly; `secure_filename`, size/MIME/extension validation; delete-data option

---

## Folder Structure

```
dia_assist/
│
├── app.py                  # Flask app entry point & routes
├── requirements.txt
├── README.md
├── .gitignore
├── sample_medical_report.txt   # Demo/test report
├── database.db             # SQLite database (auto-created)
│
├── utils/
│   ├── __init__.py
│   ├── report_parser.py    # PDF/DOCX/TXT/image text extraction
│   ├── lab_analyzer.py     # Lab value extraction + analysis
│   ├── nutrition.py        # Diet planning & calorie logic
│   ├── skin_analyzer.py    # Rule-based skin image assessment
│   ├── ai_assistant.py     # Rule-based local chatbot engine
│   └── pdf_report.py       # ReportLab PDF generation
│
├── templates/
│   ├── base.html           # Layout (sidebar, topbar, chatbot)
│   ├── index.html          # Landing page
│   ├── dashboard.html      # All analyses overview
│   ├── report.html         # Report result dashboard
│   ├── diet.html           # Diet planner
│   ├── skin.html           # Skin AI page
│   └── 404.html            # Not-found page
│
├── static/
│   ├── css/style.css
│   └── js/app.js
│
└── uploads/
    ├── reports/            # Uploaded medical reports (private)
    └── skin/               # Uploaded skin photos (private)
```

---

## Installation

### 1. Prerequisites

- **Python 3.8+** installed
- **Tesseract OCR** installed for image/PDF OCR (see below)

### 2. macOS / Linux

```bash
cd dia_assist
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

### 3. Windows

```powershell
cd dia_assist
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

### 4. Open in Chrome

Open Google Chrome and go to:

```
http://127.0.0.1:5000
```

Use **Ctrl+C** in the terminal to stop the server.

---

## OCR Installation (Tesseract)

The image/PDF OCR feature uses **pytesseract**, which is a wrapper around the **Tesseract-OCR** engine (a separate binary).

**macOS**

```bash
brew install tesseract
```

**Windows**

1. Download the installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Install it (e.g. to `C:\Program Files\Tesseract-OCR`)
3. Add the binary to your PATH, or in `app.py` set:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

**Linux (Ubuntu/Debian)**

```bash
sudo apt-get install tesseract-ocr
```

> If Tesseract is not installed, the app will still work — OCR attempts will gracefully fail with a clear message instead of crashing.

---

## How PDF Report Generation Works

1. After a medical report is analyzed, the results are stored in the SQLite database tied to an **analysis session**.
2. Clicking **Download PDF Report** calls `POST /download-report` (or `GET` with the session id).
3. `utils/pdf_report.py` uses **ReportLab** (`reportlab.platypus`) to build a multi-page PDF with:
   - Title header (**DIA ASSIST – AI HEALTH & WELLNESS REPORT**)
   - Report date
   - Patient overview
   - Key findings
   - Abnormal results table (with status badges)
   - Complete lab results table
   - Explanation of abnormal results
   - General wellness recommendations & diet guidance
   - A simple bar chart visualization of detected values (drawn via ReportLab graphics)
   - Questions for the doctor
   - Safety disclaimer
4. Page numbers and footer are added via `onPage` callbacks.
5. The PDF is streamed back to the browser as a download.

---

## Privacy

- Uploaded files are stored under `uploads/` which is **not** served as a static folder — files can never be fetched through a public URL.
- Filenames are sanitized with `werkzeug.utils.secure_filename`.
- File type is validated by extension **and** MIME type; file size capped via `MAX_CONTENT_LENGTH`.
- Lab values are only extracted when they actually appear in the uploaded report — nothing is ever invented.
- **Delete Data** (sidebar → Settings) clears uploaded files, analysis sessions and SQLite records.

---

## Safety Disclaimer

DIA ASSIST is an **educational prototype**. It does not diagnose, treat, cure, or prevent any disease. All health information provided is general wellness education and **must not replace professional medical advice**. Always discuss your results with a licensed healthcare professional.

---

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `ModuleNotFoundError: flask` | Activate your venv and run `pip install -r requirements.txt` |
| `address already in use` | Kill the old process or run on another port: `python app.py --port 5001` |
| PDF analysis extracts no text | Upload a text-based PDF, or a scanned PDF will fall back to OCR (requires Tesseract) |
| OCR not working | Install Tesseract (see above) and verify `tesseract --version` |
| DOC/DOCX not reading | Re-save the file as a newer `.docx` format |
| Images blurry | Upload a clear, well-lit image for better OCR / skin assessment |
| Port not opening in Chrome | Confirm server output shows `Running on http://127.0.0.1:5000`, then open that exact URL |

---

## Demo / Test

A sample file `sample_medical_report.txt` is included. Upload it from `/upload-report` to see the full analysis, charts, chatbot answers, diet guidance and PDF download working end-to-end.

> ⚠️ `sample_medical_report.txt` contains **DEMO / TEST DATA — NOT A REAL PATIENT**. Use it only for application testing.

---

**Made with Flask, SQLite, ReportLab, Chart.js, PyMuPDF, python-docx, Pillow, pytesseract.**