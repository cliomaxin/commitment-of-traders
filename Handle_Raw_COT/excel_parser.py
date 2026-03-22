"""
Parses CFTC historical COT spreadsheet files into the same dict format
as cot_parser.py so records save into the same CotReport model.

Supported formats:
    .xls    — CFTC legacy Excel (most historical files)
    .xlsx   — Modern Excel
    .xlsb   — Excel Binary
    .csv    — Comma-delimited text
    .ods    — OpenDocument Spreadsheet

CFTC Historical File Source:
    https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/
    Download the "Excel" zip for any year, extract, and upload the .xls inside.

CFTC Legacy XLS Column Layout (Futures-Only, "Legacy" short report):
    The file has ONE row per instrument per week. Columns are flat — there
    are no multi-level headers or merged cells like the HTML report.
    Key columns (actual names from CFTC file, some trimmed):

    Market_and_Exchange_Names       — e.g. "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"
    As_of_Date_in_Form_YYYY-MM-DD   — report date
    CFTC_Contract_Market_Code       — e.g. "090741"
    Open_Interest_All               — total open interest
    Noncommercial_Positions_Long_All
    Noncommercial_Positions_Short_All
    Noncommercial_Positions_Spreading_All
    Commercial_Positions_Long_All
    Commercial_Positions_Short_All
    Total_Reportable_Positions_Long_All
    Total_Reportable_Positions_Short_All
    Nonreportable_Positions_Long_All
    Nonreportable_Positions_Short_All
    Change_in_Open_Interest_All
    Change_in_Noncommercial_Long_All
    Change_in_Noncommercial_Short_All
    Change_in_Noncommercial_Spreading_All
    Change_in_Commercial_Long_All
    Change_in_Commercial_Short_All
    Change_in_Total_Reportable_Long_All
    Change_in_Total_Reportable_Short_All
    Change_in_Nonreportable_Long_All
    Change_in_Nonreportable_Short_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_NC_Long_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_NC_Short_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_NC_Spreading_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_Comm_Long_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_Comm_Short_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_Tot_Rept_Long_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_Tot_Rept_Short_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_NR_Long_All
    Pct_of_Open_Interest_for_Each_Category_by_Report_NR_Short_All
    Traders_in_Each_Category_Total_All
    Traders_in_Each_Category_by_Report_NonCom_Long_All
    Traders_in_Each_Category_by_Report_NonCom_Short_All
    Traders_in_Each_Category_by_Report_NonCom_Spread_All
    Traders_in_Each_Category_by_Report_Com_Long_All
    Traders_in_Each_Category_by_Report_Com_Short_All
    Traders_in_Each_Category_by_Report_Tot_Rept_Long_All
    Traders_in_Each_Category_by_Report_Tot_Rept_Short_All

Usage (standalone):
    python excel_parser.py annual_futures_2024.xls
    python excel_parser.py annual_futures_2024.xls annual_futures_2023.xls

Usage (from Django view — same as cot_parser.py):
    from .excel_parser import parse_excel_file_from_bytes

    records = parse_excel_file_from_bytes(
        file_bytes = upload.read(),
        filename   = upload.name,
    )
    # records is a list of dicts — identical keys to cot_parser.py output
    # feed straight into CotReport.objects.update_or_create()
"""

from __future__ import annotations

import io
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── dependency check ─────────────────────────────────────────────────────────
# pandas is required.  xlrd is required for .xls files.
# Install:  pip install pandas xlrd openpyxl odfpy
# xlrd >= 2.0 only supports .xls (not .xlsx) — that is exactly what we need.
try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "pandas is required: pip install pandas xlrd openpyxl odfpy"
    ) from e


# ─────────────────────────────────────────────────────────────────────────────
# TARGET INSTRUMENTS
# Mirrors cot_parser.py exactly — same canonical names so records merge into
# the same CotReport rows.
# Keys are SUBSTRINGS of the Market_and_Exchange_Names column (uppercase).
# ─────────────────────────────────────────────────────────────────────────────

TARGET_INSTRUMENTS: Dict[str, str] = {
    # Forex — 7 majors
    "EURO FX - CHICAGO":           "EURO FX",
    "BRITISH POUND - CHICAGO":     "BRITISH POUND",
    "JAPANESE YEN - CHICAGO":      "JAPANESE YEN",
    "SWISS FRANC - CHICAGO":       "SWISS FRANC",
    "CANADIAN DOLLAR - CHICAGO":   "CANADIAN DOLLAR",
    "AUSTRALIAN DOLLAR - CHICAGO": "AUSTRALIAN DOLLAR",
    "NZ DOLLAR - CHICAGO":         "NZ DOLLAR",
    # Metals
    "GOLD - COMMODITY EXCHANGE":   "GOLD",
    "SILVER - COMMODITY EXCHANGE": "SILVER",
    # Crypto
    "BITCOIN - CHICAGO":           "BITCOIN",
}


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN MAP
# Maps our internal field names to the possible column names in the CFTC file.
# CFTC has used slightly different column names across years so we provide
# multiple aliases — the first one found in the actual file is used.
# ─────────────────────────────────────────────────────────────────────────────

# Each entry: internal_name → [primary_col, alias1, alias2, ...]
COLUMN_ALIASES: Dict[str, List[str]] = {
    # ── Identity ──────────────────────────────────────────────────────────
    "market_name":    ["Market_and_Exchange_Names"],
    "report_date":    [
        "As_of_Date_in_Form_YYYY-MM-DD",
        "Report_Date_as_YYYY-MM-DD",
        "As_of_Date_in_Form_YY-MM-DD",
        "As_of_Date",
        "Report_Date",
    ],
    "cftc_code":      [
        "CFTC_Contract_Market_Code",
        "Contract_Market_Code",
        "CFTC_Market_Code",
    ],
    "contract_spec":  [
        "CFTC_Commodity_Name",
        "Commodity_Name",
        "Commodity",
    ],

    # ── Open Interest ──────────────────────────────────────────────────────
    "open_interest":  ["Open_Interest_All", "Open_Interest_(All)", "Open_Interest"],
    "oi_change":      ["Change_in_Open_Interest_All", "Change_in_Open_Interest_(All)", "Change_in_Open_Interest"],

    # ── Commitments ───────────────────────────────────────────────────────
    "nc_long":        ["Noncommercial_Positions_Long_All",       "NonComm_Positions_Long_All"],
    "nc_short":       ["Noncommercial_Positions_Short_All",      "NonComm_Positions_Short_All"],
    "nc_spreads":     ["Noncommercial_Positions_Spreading_All",  "NonComm_Positions_Spreading_All"],
    "comm_long":      ["Commercial_Positions_Long_All",          "Comm_Positions_Long_All"],
    "comm_short":     ["Commercial_Positions_Short_All",         "Comm_Positions_Short_All"],
    "total_long":     ["Total_Reportable_Positions_Long_All",    "Tot_Rept_Positions_Long_All"],
    "total_short":    ["Total_Reportable_Positions_Short_All",   "Tot_Rept_Positions_Short_All"],
    "nr_long":        ["Nonreportable_Positions_Long_All",       "NonRept_Positions_Long_All"],
    "nr_short":       ["Nonreportable_Positions_Short_All",      "NonRept_Positions_Short_All"],

    # ── Changes ───────────────────────────────────────────────────────────
    "chg_nc_long":    ["Change_in_Noncommercial_Long_All",        "Change_in_NonComm_Long_All"],
    "chg_nc_short":   ["Change_in_Noncommercial_Short_All",       "Change_in_NonComm_Short_All"],
    "chg_nc_spreads": ["Change_in_Noncommercial_Spreading_All",   "Change_in_NonComm_Spreading_All"],
    "chg_comm_long":  ["Change_in_Commercial_Long_All",           "Change_in_Comm_Long_All"],
    "chg_comm_short": ["Change_in_Commercial_Short_All",          "Change_in_Comm_Short_All"],
    "chg_total_long": ["Change_in_Total_Reportable_Long_All",     "Change_in_Tot_Rept_Long_All"],
    "chg_total_short":["Change_in_Total_Reportable_Short_All",    "Change_in_Tot_Rept_Short_All"],
    "chg_nr_long":    ["Change_in_Nonreportable_Long_All",        "Change_in_NonRept_Long_All"],
    "chg_nr_short":   ["Change_in_Nonreportable_Short_All",       "Change_in_NonRept_Short_All"],

    # ── Percent of OI ─────────────────────────────────────────────────────
    "pct_nc_long":    [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_NC_Long_All",
        "Pct_of_OI_NC_Long_All",
        "Pct_of_Open_Interest_NC_Long_All",
    ],
    "pct_nc_short":   [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_NC_Short_All",
        "Pct_of_OI_NC_Short_All",
    ],
    "pct_nc_spreads": [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_NC_Spreading_All",
        "Pct_of_OI_NC_Spreading_All",
    ],
    "pct_comm_long":  [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_Comm_Long_All",
        "Pct_of_OI_Comm_Long_All",
    ],
    "pct_comm_short": [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_Comm_Short_All",
        "Pct_of_OI_Comm_Short_All",
    ],
    "pct_total_long": [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_Tot_Rept_Long_All",
        "Pct_of_OI_Tot_Rept_Long_All",
    ],
    "pct_total_short":[
        "Pct_of_Open_Interest_for_Each_Category_by_Report_Tot_Rept_Short_All",
        "Pct_of_OI_Tot_Rept_Short_All",
    ],
    "pct_nr_long":    [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_NR_Long_All",
        "Pct_of_OI_NR_Long_All",
    ],
    "pct_nr_short":   [
        "Pct_of_Open_Interest_for_Each_Category_by_Report_NR_Short_All",
        "Pct_of_OI_NR_Short_All",
    ],

    # ── Trader counts ─────────────────────────────────────────────────────
    "traders_total":    ["Traders_in_Each_Category_Total_All",                   "Traders_Total_All"],
    "trd_nc_long":      ["Traders_in_Each_Category_by_Report_NonCom_Long_All",   "Traders_NonCom_Long_All"],
    "trd_nc_short":     ["Traders_in_Each_Category_by_Report_NonCom_Short_All",  "Traders_NonCom_Short_All"],
    "trd_nc_spreads":   ["Traders_in_Each_Category_by_Report_NonCom_Spread_All", "Traders_NonCom_Spread_All"],
    "trd_comm_long":    ["Traders_in_Each_Category_by_Report_Com_Long_All",      "Traders_Com_Long_All"],
    "trd_comm_short":   ["Traders_in_Each_Category_by_Report_Com_Short_All",     "Traders_Com_Short_All"],
    "trd_total_long":   ["Traders_in_Each_Category_by_Report_Tot_Rept_Long_All", "Traders_Tot_Rept_Long_All"],
    "trd_total_short":  ["Traders_in_Each_Category_by_Report_Tot_Rept_Short_All","Traders_Tot_Rept_Short_All"],
}


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _safe_int(val) -> int:
    """Convert a cell value to int, returning 0 on null/error."""
    try:
        if pd.isna(val):
            return 0
    except (TypeError, ValueError):
        pass
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return 0


def _safe_float(val) -> float:
    """Convert a cell value to float, returning 0.0 on null/error."""
    try:
        if pd.isna(val):
            return 0.0
    except (TypeError, ValueError):
        pass
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _safe_date(val) -> str:
    """
    Convert various date formats to 'YYYY-MM-DD' string.
    Handles: datetime objects, pandas Timestamp, 'YYYY-MM-DD' strings,
             'MM/DD/YYYY' strings, Excel serial numbers.
    Returns '' on failure.
    """
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass

    # pandas Timestamp or datetime
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")

    s = str(val).strip()

    # Already YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # MM/DD/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return "{}-{:02d}-{:02d}".format(m.group(3), int(m.group(1)), int(m.group(2)))

    # YY-MM-DD (old CFTC format)
    m = re.match(r"^(\d{2})-(\d{2})-(\d{2})$", s)
    if m:
        yr = int(m.group(1))
        yr += 2000 if yr < 50 else 1900
        return "{}-{}-{}".format(yr, m.group(2), m.group(3))

    # Try pandas parse as last resort
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _build_column_map(df_columns: List[str]) -> Dict[str, str]:
    """
    Build a mapping: internal_field_name → actual_df_column_name
    by scanning the aliases for each field against the real column list.
    Columns are matched case-insensitively and with spaces normalised to _.
    """
    # Normalise actual columns for matching
    normalised = {
        col.strip().replace(" ", "_"): col
        for col in df_columns
    }
    normalised_upper = {k.upper(): v for k, v in normalised.items()}

    col_map: Dict[str, str] = {}
    missing: List[str] = []

    for field, aliases in COLUMN_ALIASES.items():
        found = False
        for alias in aliases:
            key = alias.strip().replace(" ", "_").upper()
            if key in normalised_upper:
                col_map[field] = normalised_upper[key]
                found = True
                break
        if not found:
            missing.append(field)

    if missing:
        print("  [WARN] Could not map columns: {}".format(", ".join(missing)))

    return col_map


def _match_instrument(market_name: str) -> Optional[str]:
    """
    Given a market name cell value, return the canonical instrument name
    or None if it is not one of the 10 targets.
    """
    upper = str(market_name).upper().strip()
    for key, canonical in TARGET_INSTRUMENTS.items():
        if key.upper() in upper:
            return canonical
    return None


def _load_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Load a file from raw bytes into a pandas DataFrame.
    Handles: .xls, .xlsx, .xlsb, .csv, .ods
    """
    ext = Path(filename).suffix.lower()
    buf = io.BytesIO(file_bytes)

    if ext == ".csv":
        # Try UTF-8 first, fall back to latin-1 (common in CFTC files)
        try:
            return pd.read_csv(buf, low_memory=False)
        except UnicodeDecodeError:
            buf.seek(0)
            return pd.read_csv(buf, encoding="latin-1", low_memory=False)

    if ext == ".xls":
        # xlrd handles .xls only — make sure xlrd is installed
        try:
            return pd.read_excel(buf, engine="xlrd")
        except Exception as e:
            raise ImportError(
                ".xls files require xlrd: pip install xlrd"
            ) from e

    if ext in (".xlsx", ".xlsm"):
        return pd.read_excel(buf, engine="openpyxl")

    if ext == ".xlsb":
        try:
            return pd.read_excel(buf, engine="pyxlsb")
        except Exception as e:
            raise ImportError(
                ".xlsb files require pyxlsb: pip install pyxlsb"
            ) from e

    if ext == ".ods":
        try:
            return pd.read_excel(buf, engine="odf")
        except Exception as e:
            raise ImportError(
                ".ods files require odfpy: pip install odfpy"
            ) from e

    # Unknown extension — try openpyxl as fallback
    return pd.read_excel(buf, engine="openpyxl")


def _row_to_dict(row: "pd.Series", col_map: Dict[str, str],
                 source_file: str) -> Optional[dict]:
    """
    Convert one DataFrame row to a CotReport-compatible dict.
    Returns None if the row cannot be mapped.
    """
    def get(field: str, default=None):
        col = col_map.get(field)
        if col is None:
            return default
        return row.get(col, default)

    # ── Report date ───────────────────────────────────────────────────────
    as_of_date = _safe_date(get("report_date"))
    if not as_of_date:
        return None

    # ── Instrument name ───────────────────────────────────────────────────
    market_raw = get("market_name", "")
    canonical  = _match_instrument(market_raw)
    if canonical is None:
        return None

    # ── CFTC code ─────────────────────────────────────────────────────────
    code = str(get("cftc_code", "")).strip()

    # ── Contract spec ─────────────────────────────────────────────────────
    contract_spec = str(get("contract_spec", "")).strip()

    # ── Build record ─────────────────────────────────────────────────────
    rec: dict = {
        "name":          canonical,
        "code":          code,
        "source_file":   source_file,
        "as_of_date":    as_of_date,
        "prev_date":     "",           # not available in flat XLS format
        "contract_spec": contract_spec,

        # Open interest
        "open_interest": _safe_int(get("open_interest",  0)),
        "oi_change":     _safe_int(get("oi_change",       0)),

        # Commitments
        "nc_long":       _safe_int(get("nc_long",         0)),
        "nc_short":      _safe_int(get("nc_short",        0)),
        "nc_spreads":    _safe_int(get("nc_spreads",      0)),
        "comm_long":     _safe_int(get("comm_long",       0)),
        "comm_short":    _safe_int(get("comm_short",      0)),
        "total_long":    _safe_int(get("total_long",      0)),
        "total_short":   _safe_int(get("total_short",     0)),
        "nr_long":       _safe_int(get("nr_long",         0)),
        "nr_short":      _safe_int(get("nr_short",        0)),

        # Changes
        "chg_nc_long":    _safe_int(get("chg_nc_long",    0)),
        "chg_nc_short":   _safe_int(get("chg_nc_short",   0)),
        "chg_nc_spreads": _safe_int(get("chg_nc_spreads", 0)),
        "chg_comm_long":  _safe_int(get("chg_comm_long",  0)),
        "chg_comm_short": _safe_int(get("chg_comm_short", 0)),
        "chg_total_long": _safe_int(get("chg_total_long", 0)),
        "chg_total_short":_safe_int(get("chg_total_short",0)),
        "chg_nr_long":    _safe_int(get("chg_nr_long",    0)),
        "chg_nr_short":   _safe_int(get("chg_nr_short",   0)),

        # Percent of OI
        "pct_nc_long":    _safe_float(get("pct_nc_long",    0)),
        "pct_nc_short":   _safe_float(get("pct_nc_short",   0)),
        "pct_nc_spreads": _safe_float(get("pct_nc_spreads", 0)),
        "pct_comm_long":  _safe_float(get("pct_comm_long",  0)),
        "pct_comm_short": _safe_float(get("pct_comm_short", 0)),
        "pct_total_long": _safe_float(get("pct_total_long", 0)),
        "pct_total_short":_safe_float(get("pct_total_short",0)),
        "pct_nr_long":    _safe_float(get("pct_nr_long",    0)),
        "pct_nr_short":   _safe_float(get("pct_nr_short",   0)),

        # Trader counts
        "traders_total":  _safe_int(get("traders_total",  0)),
        "trd_nc_long":    _safe_int(get("trd_nc_long",    0)),
        "trd_nc_short":   _safe_int(get("trd_nc_short",   0)),
        "trd_nc_spreads": _safe_int(get("trd_nc_spreads", 0)),
        "trd_comm_long":  _safe_int(get("trd_comm_long",  0)),
        "trd_comm_short": _safe_int(get("trd_comm_short", 0)),
        "trd_total_long": _safe_int(get("trd_total_long", 0)),
        "trd_total_short":_safe_int(get("trd_total_short",0)),
    }

    return rec


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — mirrors cot_parser.py interface
# ─────────────────────────────────────────────────────────────────────────────

def parse_excel_file_from_bytes(file_bytes: bytes,
                                filename: str = "upload") -> List[dict]:
    """
    Parse a CFTC COT spreadsheet file from raw bytes.
    Called by the Django upload view — file bytes come from request.FILES.

    Parameters
    ----------
    file_bytes : bytes
        Raw file content from upload.read()
    filename   : str
        Original filename for source_file tracing and format detection.
        Must include the extension: .xls, .xlsx, .csv, .xlsb, .ods

    Returns
    -------
    list[dict]
        One dict per matched target instrument row found in the file.
        Dict keys are identical to cot_parser.parse_cot_file_from_text().
        Feed directly into CotReport.objects.update_or_create().
    """
    try:
        df = _load_dataframe(file_bytes, filename)
    except Exception as exc:
        raise ValueError(
            "Could not read file '{}': {}".format(filename, exc)
        )

    # Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    col_map = _build_column_map(list(df.columns))

    # Verify we have the minimum required columns
    required = {"market_name", "report_date", "open_interest", "nc_long"}
    missing_required = required - set(col_map.keys())
    if missing_required:
        raise ValueError(
            "File '{}' is missing required columns: {}. "
            "Are you uploading a CFTC Legacy Futures-Only file?".format(
                filename, ", ".join(missing_required)
            )
        )

    results: List[dict] = []

    for _, row in df.iterrows():
        market_name = row.get(col_map.get("market_name", ""), "")
        canonical   = _match_instrument(market_name)
        if canonical is None:
            continue  # not a target instrument — skip quickly

        rec = _row_to_dict(row, col_map, source_file=filename)
        if rec is not None:
            results.append(rec)

    return results


def parse_excel_file(filepath: str) -> List[dict]:
    """
    Parse a CFTC COT spreadsheet from a file path on disk.
    Convenience wrapper around parse_excel_file_from_bytes() for CLI use.
    """
    path = Path(filepath)
    file_bytes = path.read_bytes()
    return parse_excel_file_from_bytes(file_bytes, filename=path.name)


def parse_excel_files(filepaths: List[str]) -> List[dict]:
    """
    Parse multiple CFTC COT spreadsheet files.
    Deduplicates by (name, as_of_date) — later files win on conflict.

    Parameters
    ----------
    filepaths : list of str
        Paths to .xls / .xlsx / .csv / .xlsb / .ods files.

    Returns
    -------
    list[dict]
        Deduplicated records across all files.
    """
    seen: Dict[Tuple[str, str], dict] = {}

    for fp in filepaths:
        print("\nParsing: {}".format(fp))
        try:
            records = parse_excel_file(fp)
        except Exception as exc:
            print("  [ERROR] {}: {}".format(fp, exc))
            continue

        for rec in records:
            key = (rec["name"], rec["as_of_date"])
            if key in seen:
                print("  [SKIP] Duplicate: {} {}".format(rec["name"], rec["as_of_date"]))
            else:
                seen[key] = rec
                print("  [OK] {:<22} as_of={}  OI={:,}".format(
                    rec["name"], rec["as_of_date"], rec["open_interest"]
                ))

    return list(seen.values())


# ─────────────────────────────────────────────────────────────────────────────
# CLI — python excel_parser.py file1.xls file2.xls
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python excel_parser.py <file1.xls> [file2.xls ...]")
        print("\nSupported: .xls .xlsx .xlsb .csv .ods")
        print("Source:    https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/")
        sys.exit(1)

    records = parse_excel_files(sys.argv[1:])

    print("\n" + "─" * 60)
    print("Total matched records: {}".format(len(records)))
    print("─" * 60)
    print(json.dumps(records, indent=2, default=str))
