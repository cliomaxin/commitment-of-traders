# ══════════════════════════════════════════════════════════════════════════════
# PROJECT CONTEXT — Maksim Felix COT Dashboard
# ══════════════════════════════════════════════════════════════════════════════
# Paste this entire file as context into your AI agent (Copilot Chat,
# Cursor, Continue, Claude Dev, etc.) before asking it to fix any error.
# The agent will understand the full structure, every file, every model
# field, and every design decision without you having to re-explain.
# ══════════════════════════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────────────────────────
# 1. WHAT THIS PROJECT IS
# ─────────────────────────────────────────────────────────────────────────────

"""
Maksim Felix COT Dashboard is a Django web application that:

  1. Accepts uploaded CFTC (Commodity Futures Trading Commission) HTML files
     from the user through a browser upload form.

  2. Parses the uploaded files using a custom Python parser (cot_parser.py)
     that extracts COT (Commitments of Traders) data for 10 specific
     financial instruments.

  3. Saves the extracted data into a PostgreSQL (or SQLite) database
     through Django models.

  4. Displays the saved data in a styled dashboard with tables showing
     positions, weekly changes, percentages, and trader counts for each
     instrument.

The COT report is published every Friday by the CFTC. It shows how three
categories of traders (Non-Commercial, Commercial, Nonreportable) are
positioned in futures markets — long, short, and spreading. Traders and
analysts use this data to gauge market sentiment and positioning extremes.
"""


# ─────────────────────────────────────────────────────────────────────────────
# 2. TECH STACK
# ─────────────────────────────────────────────────────────────────────────────

"""
Language        : Python (latest installed version — NOT Python 3.7)
Framework       : Django (latest)
Database        : SQLite (development) / PostgreSQL (production)
Frontend        : Plain HTML + CSS + Vanilla JavaScript (no React, no Vue)
Fonts           : Google Fonts — DM Serif Display, DM Mono, DM Sans
File uploads    : Django forms + request.FILES (no third-party upload lib)
AJAX            : Native fetch() API — no jQuery
Styling         : Custom CSS with CSS variables — no Tailwind, no Bootstrap

The project has NO external JS dependencies. Everything runs from Django's
built-in development server during development.
"""


# ─────────────────────────────────────────────────────────────────────────────
# 3. PROJECT FOLDER STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

"""
Commitment Of Traders/              ← root project folder on desktop
└── COT/                            ← Django project root (manage.py lives here)
    ├── manage.py
    ├── COT/                        ← Django project settings package
    │   ├── __init__.py
    │   ├── settings.py
    │   ├── urls.py                 ← root URL config
    │   └── wsgi.py
    │
    ├── Handle_Raw_COT/             ← APP 1: data ingestion
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── cot_parser.py           ← HTML parser engine
    │   ├── forms.py                ← upload form (MultipleFileField)
    │   ├── models.py               ← ImportLog, CotReport, CotReportHistory
    │   ├── urls.py
    │   ├── views.py                ← CotUploadView (GET + POST)
    │   └── templates/
    │       └── Handle_Raw_COT/
    │           └── upload.html     ← drag-and-drop upload page
    │
    └── COT_Display/                ← APP 2: data display (dashboard)
        ├── __init__.py
        ├── admin.py
        ├── apps.py
        ├── models.py               ← no models — reads from Handle_Raw_COT
        ├── urls.py
        ├── views.py                ← dashboard, detail, history views
        └── templates/
            └── COT_Display/
                └── dashboard.html  ← main display page with COT tables
"""


# ─────────────────────────────────────────────────────────────────────────────
# 4. THE TWO APPS EXPLAINED
# ─────────────────────────────────────────────────────────────────────────────

"""
APP 1 — Handle_Raw_COT
──────────────────────
Purpose : Take raw CFTC HTML files from the user, parse them, and persist
          the extracted data into the database.

Entry point : /cot/upload/   →   Handle_Raw_COT.views.CotUploadView

Flow:
  1. User visits /cot/upload/ (GET) → sees the upload form (upload.html)
  2. User selects one or more .htm files and submits (POST)
  3. View reads ALL files via request.FILES.getlist("files")
  4. Each file is decoded (UTF-8) and passed to parse_cot_file_from_text()
  5. Parser returns a list of dicts — one per matched instrument
  6. View calls CotReport.objects.update_or_create() for each dict
  7. An ImportLog row is written recording the outcome
  8. A JSON response (AJAX) or redirect is returned to the browser

Key files:
  cot_parser.py   — the parsing engine (pure Python, no Django dependency)
  forms.py        — CotUploadForm using MultipleFileField / MultipleFileInput
                    (does NOT use ClearableFileInput — incompatible with
                    multiple file uploads on older Django)
  models.py       — ImportLog, CotReport, CotReportHistory (see Section 6)
  views.py        — CotUploadView class-based view
  upload.html     — drag-and-drop UI with AJAX submission and results panel


APP 2 — COT_Display
────────────────────
Purpose : Read the data saved by Handle_Raw_COT and display it in a
          structured, styled dashboard.

Entry point : /dashboard/   →   COT_Display.views (dashboard view)

This app has NO models of its own. It imports and queries CotReport
directly from Handle_Raw_COT.models.

Key responsibilities:
  - Show the latest week's data for all 10 instruments in one table
  - Allow filtering by asset class (Forex / Metal / Crypto)
  - Show week-over-week changes with colour coding (green = positive,
    red = negative)
  - Show historical data for a single instrument on a detail page
  - The table structure matches the CFTC source exactly (see Section 7)
"""


# ─────────────────────────────────────────────────────────────────────────────
# 5. THE 10 TARGET INSTRUMENTS
# ─────────────────────────────────────────────────────────────────────────────

"""
The parser extracts ONLY these 10 instruments and ignores everything else.

  Asset Class  Name (stored in DB)   CFTC Name in file          Source file
  ───────────  ──────────────────    ────────────────────────   ───────────
  forex        EURO FX               EURO FX - CHICAGO ...      deacmesf.htm
  forex        BRITISH POUND         BRITISH POUND - CHICAGO    deacmesf.htm
  forex        JAPANESE YEN          JAPANESE YEN - CHICAGO     deacmesf.htm
  forex        SWISS FRANC           SWISS FRANC - CHICAGO      deacmesf.htm
  forex        CANADIAN DOLLAR       CANADIAN DOLLAR - CHICAGO  deacmesf.htm
  forex        AUSTRALIAN DOLLAR     AUSTRALIAN DOLLAR - CME    deacmesf.htm
  forex        NZ DOLLAR             NZ DOLLAR - CHICAGO        deacmesf.htm
  metal        GOLD                  GOLD - COMMODITY EXCHANGE  deacmxsf.htm
  metal        SILVER                SILVER - COMMODITY EXCH.   deacmxsf.htm
  crypto       BITCOIN               BITCOIN - CHICAGO          deacmesf.htm

The TARGET_INSTRUMENTS dict in cot_parser.py maps unique substrings of the
CFTC header line to these canonical names. The substrings are deliberately
specific to avoid false positives (e.g. "EURO FX - CHICAGO" avoids matching
"EURO FX/BRITISH POUND XRATE", and "GOLD - COMMODITY EXCHANGE" avoids
"MICRO GOLD").

Download URLs:
  https://www.cftc.gov/dea/futures/deacmesf.htm  (FX + Bitcoin)
  https://www.cftc.gov/dea/futures/deacmxsf.htm  (Gold + Silver)
"""


# ─────────────────────────────────────────────────────────────────────────────
# 6. DATABASE MODELS  (Handle_Raw_COT/models.py)
# ─────────────────────────────────────────────────────────────────────────────

"""
Three models:

┌─────────────────────────────────────────────────────────────────────────────
│ ImportLog
├─────────────────────────────────────────────────────────────────────────────
│ Tracks every upload session. One row per uploaded file.
│
│ Fields:
│   uploaded_by      ForeignKey(User, null=True)   who uploaded
│   uploaded_at      DateTimeField                 when upload started
│   filename         CharField(255)                e.g. "deacmesf.htm"
│   file_size_kb     PositiveIntegerField          approximate size
│   status           CharField  pending|success|partial|failed
│   instruments_found PositiveSmallIntegerField    how many instruments parsed
│   records_created  PositiveSmallIntegerField     new DB rows created
│   records_updated  PositiveSmallIntegerField     existing rows updated
│   error_detail     TextField(blank=True)         any parse/save errors
│   completed_at     DateTimeField(null=True)      when processing finished
│
│ Method:  mark_complete(created, updated, errors)
│   Call after processing to set status, counts, and completed_at in one hit.


┌─────────────────────────────────────────────────────────────────────────────
│ CotReport
├─────────────────────────────────────────────────────────────────────────────
│ One row = one instrument + one reporting week.
│ UniqueConstraint on (name, as_of_date) — no duplicates per week.
│
│ Identity fields:
│   name             CharField  choices=INSTRUMENT_CHOICES  e.g. "EURO FX"
│   code             CharField  CFTC code e.g. "099741"
│   asset_class      CharField  choices: forex|metal|crypto  (auto-set on save)
│   contract_spec    CharField  e.g. "CONTRACTS OF EUR 125,000"
│   as_of_date       DateField  CFTC report date (Tuesday of reporting week)
│   prev_date        DateField  prior week date
│   source_file      CharField  original filename
│   import_log       ForeignKey(ImportLog, null=True)
│   open_interest    BigIntegerField
│   oi_change        BigIntegerField  signed — change in OI from prior week
│
│ Commitments (9 fields):
│   nc_long, nc_short, nc_spreads          Non-Commercial positions
│   comm_long, comm_short                  Commercial positions
│   total_long, total_short                Total positions
│   nr_long, nr_short                      Nonreportable positions
│
│ Changes from prior week (9 fields, same layout, prefix chg_):
│   chg_nc_long, chg_nc_short, chg_nc_spreads
│   chg_comm_long, chg_comm_short
│   chg_total_long, chg_total_short
│   chg_nr_long, chg_nr_short
│
│ Percent of open interest (9 fields, DecimalField 6,2, prefix pct_):
│   pct_nc_long, pct_nc_short, pct_nc_spreads
│   pct_comm_long, pct_comm_short
│   pct_total_long, pct_total_short
│   pct_nr_long, pct_nr_short
│
│ Trader counts (8 fields):
│   traders_total
│   trd_nc_long, trd_nc_short, trd_nc_spreads
│   trd_comm_long, trd_comm_short
│   trd_total_long, trd_total_short
│   (NR trader columns are blank in the CFTC source — not stored)
│
│ Timestamps:
│   created_at   DateTimeField(auto_now_add=True)
│   updated_at   DateTimeField(auto_now=True)
│
│ Computed properties (not stored in DB):
│   net_nc_position    →  nc_long - nc_short
│   net_comm_position  →  comm_long - comm_short
│   nc_sentiment       →  "bullish" | "bearish" | "neutral"
│
│ Class methods:
│   latest_report_date()           →  most recent as_of_date
│   latest_for_all_instruments()   →  QuerySet for all 10 at latest date
│   history_for(name, weeks=52)    →  historical rows for one instrument
│   defaults_from_dict(data, log)  →  builds defaults dict for update_or_create


┌─────────────────────────────────────────────────────────────────────────────
│ CotReportHistory  (audit trail — optional)
├─────────────────────────────────────────────────────────────────────────────
│ Written when an existing CotReport row is overwritten by a re-import.
│ Stores a snapshot of all numeric fields before overwrite.
│
│ Fields: report (FK), snapshotted_at, import_log (FK),
│         + all numeric fields from CotReport (oi, commitments,
│           changes, pct, traders)
│
│ Class method:
│   snapshot(report, import_log)  →  saves current values before overwrite
"""


# ─────────────────────────────────────────────────────────────────────────────
# 7. COT TABLE STRUCTURE (mirrors CFTC source exactly)
# ─────────────────────────────────────────────────────────────────────────────

"""
Each instrument block in the CFTC HTML file contains a fixed-width text
block inside a <pre> tag. It has this structure:

  INSTRUMENT NAME - EXCHANGE                          Code-XXXXXX
  FUTURES ONLY POSITIONS AS OF MM/DD/YY
  ──────────────────────────────────────────────────| NONREPORTABLE
        NON-COMMERCIAL      |   COMMERCIAL    |  TOTAL  |   POSITIONS
  ──────────────────────────────────────────────────────────────────
    LONG  | SHORT  |SPREADS |  LONG  | SHORT  |  LONG  | SHORT | LONG | SHORT
  ──────────────────────────────────────────────────────────────────────────
  (CONTRACT SPEC)                         OPEN INTEREST: 247,753
  COMMITMENTS
     66,507   65,621    7,021  144,314  150,520  217,842  223,162   29,911  24,591

  CHANGES FROM MM/DD/YY (CHANGE IN OPEN INTEREST: -40,639)
    -27,392    7,881   -6,308   -1,355  -39,509  -35,055  -37,936   -5,584  -2,703

  PERCENT OF OPEN INTEREST FOR EACH CATEGORY OF TRADERS
      26.8     26.5      2.8     58.2     60.8     87.9     90.1     12.1    9.9

  NUMBER OF TRADERS IN EACH CATEGORY (TOTAL TRADERS: 121)
        27       31       14       46       33       81       70

The 9-column layout is:
  Col 1  NC Long       col 2  NC Short      col 3  NC Spreads
  Col 4  Comm Long     col 5  Comm Short
  Col 6  Total Long    col 7  Total Short
  Col 8  NR Long       col 9  NR Short

Trader counts only have 7 values (NR is blank in source).
"""


# ─────────────────────────────────────────────────────────────────────────────
# 8. THE PARSER  (Handle_Raw_COT/cot_parser.py)
# ─────────────────────────────────────────────────────────────────────────────

"""
Pure Python — no Django dependency. Can be run standalone from the CLI.

Public functions:
  parse_cot_file(path)
      Reads an .htm file from disk. Returns list of dicts.

  parse_cot_files([path1, path2, ...])
      Reads multiple files, deduplicates by (name, as_of_date).

  parse_cot_file_from_text(html_text, source_file="upload")
      ← THIS IS WHAT THE VIEW CALLS.
      Accepts HTML already read into memory (from request.FILES).
      Identical output to parse_cot_file() but no disk I/O.

Internal pipeline:
  Step 1  _extract_pre_text(html)        — pulls text from <pre> tags
  Step 2  _split_into_blocks(text)       — splits on instrument header lines
  Step 3  _parse_block(header, body)     — extracts all fields from one block
           uses _get_9_nums() and _get_9_floats() for data rows
           uses regex for dates, OI, code, contract spec

Return dict keys per instrument (40 fields):
  name, code, source_file, as_of_date, prev_date, contract_spec,
  open_interest, oi_change,
  nc_long, nc_short, nc_spreads, comm_long, comm_short,
  total_long, total_short, nr_long, nr_short,
  chg_nc_long, chg_nc_short, chg_nc_spreads, chg_comm_long, chg_comm_short,
  chg_total_long, chg_total_short, chg_nr_long, chg_nr_short,
  pct_nc_long, pct_nc_short, pct_nc_spreads, pct_comm_long, pct_comm_short,
  pct_total_long, pct_total_short, pct_nr_long, pct_nr_short,
  traders_total, trd_nc_long, trd_nc_short, trd_nc_spreads,
  trd_comm_long, trd_comm_short, trd_total_long, trd_total_short
"""


# ─────────────────────────────────────────────────────────────────────────────
# 9. FORMS  (Handle_Raw_COT/forms.py)
# ─────────────────────────────────────────────────────────────────────────────

"""
CRITICAL — do NOT use forms.ClearableFileInput(attrs={"multiple": True}).
That raises ValueError on Django < 4.0 and still causes issues on some
versions because ClearableFileInput was never designed for multiple files.

The correct approach used here:

  class MultipleFileInput(forms.FileInput):
      # Inherits from FileInput — NOT ClearableFileInput
      # Adds multiple="multiple" and accept=".htm,.html" as HTML attrs
      # value_from_datadict() returns the FIRST file only so Django's
      # FileField.clean() passes — the VIEW reads ALL files via getlist()

  class MultipleFileField(forms.FileField):
      # Forces widget=MultipleFileInput() in __init__
      # Prevents Django from ever substituting ClearableFileInput

  class CotUploadForm(forms.Form):
      files = MultipleFileField(...)

In the VIEW, always read files like this:
    uploaded_files = request.FILES.getlist("files")
Never use form.cleaned_data["files"] to get the full list —
it only contains the first file.
"""


# ─────────────────────────────────────────────────────────────────────────────
# 10. VIEWS  (Handle_Raw_COT/views.py)
# ─────────────────────────────────────────────────────────────────────────────

"""
CotUploadView(View)

  GET  /cot/upload/
    - Instantiates CotUploadForm
    - Queries CotReport.objects.order_by("-as_of_date", "name")[:30]
    - Renders upload.html with {form, recent}

  POST /cot/upload/
    - Detects AJAX via X-Requested-With header (falls back to META)
    - Reads request.FILES.getlist("files")
    - For each file:
        1. Extension check (.htm / .html)
        2. Creates ImportLog(status="pending")
        3. Decodes bytes → UTF-8 text
        4. Calls parse_cot_file_from_text(html_text, source_file=filename)
        5. For each parsed record:
             CotReport.objects.update_or_create(
                 name=..., as_of_date=...,
                 defaults=CotReport.defaults_from_dict(rec, import_log=log)
             )
        6. Calls log.mark_complete(created, updated, errors)
    - Returns JsonResponse (AJAX) or renders upload.html with results (POST)

Helper function  _is_ajax(request):
    Checks request.headers (Django 2.2+) with fallback to request.META
    so it works on all Django versions.
"""


# ─────────────────────────────────────────────────────────────────────────────
# 11. URL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

"""
COT/urls.py  (project root):
    path("cot/",       include("Handle_Raw_COT.urls")),
    path("dashboard/", include("COT_Display.urls")),

Handle_Raw_COT/urls.py:
    app_name = "Handle_Raw_COT"
    path("upload/", CotUploadView.as_view(), name="upload"),

COT_Display/urls.py:
    app_name = "COT_Display"
    path("",         dashboard_view,  name="dashboard"),
    path("<str:name>/", detail_view,  name="detail"),
"""


# ─────────────────────────────────────────────────────────────────────────────
# 12. UPLOAD PAGE UI  (upload.html)
# ─────────────────────────────────────────────────────────────────────────────

"""
Design: dark theme (#0d0f12 background), gold accents (#c9a84b),
        DM Serif Display / DM Mono / DM Sans fonts.

Layout: two-column grid
  Left column:
    - Drag-and-drop drop zone (click or drag files onto it)
    - Selected files list (shows filename + size, each removable)
    - Progress bar (animates during upload)
    - Import button + Clear button

  Right column:
    - "Recently Imported" table showing last 30 CotReport rows:
      columns: Instrument | As Of | Open Interest | NC Net

After successful AJAX POST the left column shows a results panel:
  - Summary stats (instruments found / created / updated / errors)
  - Per-file accordion (click to expand → list of instruments found)
  - Error messages if any files failed

The form does NOT do a full page reload — it uses fetch() to POST
and renders the JSON response inline.

JavaScript responsibilities (inline, no libraries):
  - Drag-and-drop event handling
  - Custom file list management (selectedFiles array)
  - Building FormData from the selectedFiles array
  - Animating the progress bar during upload
  - Rendering the results panel from the JSON response
  - Accordion toggle for per-file instrument breakdown
"""


# ─────────────────────────────────────────────────────────────────────────────
# 13. DISPLAY APP  (COT_Display)
# ─────────────────────────────────────────────────────────────────────────────

"""
This app has NO models. It reads directly from Handle_Raw_COT.models.CotReport.

Views to implement:
  dashboard_view(request)
    - Calls CotReport.latest_for_all_instruments() — one query, all 10 rows
    - Groups by asset_class: forex / metal / crypto
    - Context: {instruments, report_date, forex_list, metal_list, crypto_list}
    - Template: COT_Display/dashboard.html

  detail_view(request, name)
    - Calls CotReport.history_for(name, weeks=52)
    - Shows historical table + net position trend
    - Context: {instrument_name, history}

The dashboard table columns match the CFTC layout exactly:
  Instrument | OI | NC Long | NC Short | NC Spread | Comm L | Comm S |
  Total L | Total S | NR L | NR S | Traders

Change rows show green for positive, red for negative values.
The header has the Maksim Felix logo + nav links: Import | Dashboard |
Analytics | Signals | Contact.
"""


# ─────────────────────────────────────────────────────────────────────────────
# 14. SETTINGS NOTES  (COT/settings.py)
# ─────────────────────────────────────────────────────────────────────────────

"""
INSTALLED_APPS must include:
    "Handle_Raw_COT",
    "COT_Display",

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB (CFTC files ~200 KB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # same

TEMPLATES[0]["DIRS"] should include the project-level templates folder
if you have shared base templates.

Each app uses its own templates/ subfolder following Django's convention:
    Handle_Raw_COT/templates/Handle_Raw_COT/upload.html
    COT_Display/templates/COT_Display/dashboard.html
"""


# ─────────────────────────────────────────────────────────────────────────────
# 15. COMMON ERRORS AND THEIR FIXES
# ─────────────────────────────────────────────────────────────────────────────

"""
ERROR 1:
  ValueError: ClearableFileInput doesn't support uploading multiple files.
  File: django/forms/widgets.py line 393

  CAUSE:  forms.py is using ClearableFileInput(attrs={"multiple": True}).
          This is banned on older Django and unreliable on all versions.

  FIX:    forms.py must use MultipleFileInput(forms.FileInput) — a custom
          widget that inherits from FileInput, NOT ClearableFileInput.
          See Section 9 above. Never use ClearableFileInput for multiple files.


ERROR 2:
  ImportError: cannot import name 'parse_cot_file_from_text' from
  'Handle_Raw_COT.cot_parser'

  CAUSE:  The function parse_cot_file_from_text() was missing from
          cot_parser.py — it was only described in a comment.

  FIX:    Add parse_cot_file_from_text(html_text, source_file) as a real
          function in cot_parser.py. It is identical to parse_cot_file()
          except it takes an html_text string instead of a file path.


ERROR 3:
  Error path shows Python37 even after installing a newer Python.

  CAUSE:  The terminal / virtual environment is still using the old Python.
          Installing a new Python does not automatically switch the active
          environment.

  FIX:
    1. deactivate (if in a venv)
    2. Delete the old venv folder
    3. py -3.12 -m venv venv        (use the new Python explicitly)
    4. venv\Scripts\activate
    5. pip install django
    6. Confirm: python --version  and  python -m django --version


ERROR 4:
  TemplateDoesNotExist: Handle_Raw_COT/upload.html

  CAUSE:  Template is in the wrong folder, or APP_DIRS is False, or
          the app is not in INSTALLED_APPS.

  FIX:    File must be at:
            Handle_Raw_COT/templates/Handle_Raw_COT/upload.html
          And settings.py must have:
            TEMPLATES[0]["APP_DIRS"] = True
            "Handle_Raw_COT" in INSTALLED_APPS


ERROR 5:
  django.db.utils.OperationalError: no such table: Handle_Raw_COT_cotreport

  CAUSE:  Migrations have not been run.

  FIX:
    python manage.py makemigrations Handle_Raw_COT
    python manage.py migrate


ERROR 6:
  AttributeError: type object 'CotReport' has no attribute 'defaults_from_dict'

  CAUSE:  The models.py in use is an old version without the
          defaults_from_dict() classmethod.

  FIX:    Replace models.py with the latest version (see Section 6).
          The method signature is:
            @staticmethod
            def defaults_from_dict(data: dict, import_log=None) -> dict
"""


# ─────────────────────────────────────────────────────────────────────────────
# 16. HOW TO USE THIS FILE WITH YOUR AI AGENT
# ─────────────────────────────────────────────────────────────────────────────

"""
In VS Code with GitHub Copilot Chat / Cursor / Continue:

  Option A — Paste as context:
    Open the chat panel, paste this entire file, then describe your error.
    e.g. "I'm getting [error]. Here is my project context above. Fix it."

  Option B — Add as workspace instruction (Cursor / Continue):
    Save this file as  .cursor/PROJECT_CONTEXT.py  or
    .continue/context.py  in your project root.
    The agent will pick it up automatically for every conversation.

  Option C — Reference specific sections:
    "See Section 9 (Forms) in my context file — fix my forms.py to match
    the MultipleFileField pattern described there."

When reporting an error to the agent, always include:
  1. The full traceback (copy from terminal)
  2. The file where the error occurs
  3. A note of which section of this document is relevant

The agent can then suggest a fix that is consistent with the rest of the
project without you having to re-explain the architecture every time.
"""
