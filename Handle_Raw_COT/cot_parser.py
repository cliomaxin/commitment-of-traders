"""
cot_parser.py
=============
Parses CFTC Commitments of Traders HTML files (the fixed-width <pre> block
format served at cftc.gov) and extracts the nine instruments you care about:

    Forex (7 majors)   — EUR/USD, GBP/USD, JPY/USD, CHF/USD,
                          CAD/USD, AUD/USD, NZD/USD
    Metals             — Gold, Silver
    Crypto             — Bitcoin

Instruments can live across multiple HTML files:
    Forex + Bitcoin    →  deacmesf.htm   (CME file)
    Gold + Silver      →  deacmxsf.htm   (CMX file)

Usage
-----
    from cot_parser import parse_cot_files

    results = parse_cot_files([
        "deacmesf.htm",   # forex + bitcoin
        "deacmxsf.htm",   # gold + silver
    ])

    for instrument in results:
        print(instrument)

    # Or integrate with Django:
    #   CotReport.objects.bulk_create([
    #       CotReport(**r) for r in results
    #   ])

Each result dict contains:
    name              str   — canonical name, e.g. "EURO FX"
    code              str   — CFTC instrument code
    source_file       str   — filename this was parsed from
    as_of_date        str   — "YYYY-MM-DD"
    prev_date         str   — "YYYY-MM-DD" (date of the prior week)
    contract_spec     str   — e.g. "CONTRACTS OF EUR 125,000"
    open_interest     int
    oi_change         int   — change in OI from prior week
    nc_long           int
    nc_short          int
    nc_spreads        int
    comm_long         int
    comm_short        int
    total_long        int
    total_short       int
    nr_long           int
    nr_short          int
    chg_nc_long       int
    chg_nc_short      int
    chg_nc_spreads    int
    chg_comm_long     int
    chg_comm_short    int
    chg_total_long    int
    chg_total_short   int
    chg_nr_long       int
    chg_nr_short      int
    pct_nc_long       float
    pct_nc_short      float
    pct_nc_spreads    float
    pct_comm_long     float
    pct_comm_short    float
    pct_total_long    float
    pct_total_short   float
    pct_nr_long       float
    pct_nr_short      float
    traders_total     int
    trd_nc_long       int
    trd_nc_short      int
    trd_nc_spreads    int
    trd_comm_long     int
    trd_comm_short    int
    trd_total_long    int
    trd_total_short   int
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple, Union


# ──────────────────────────────────────────────────────────────────────────────
# TARGET INSTRUMENTS
# Keys are substrings that must appear in the instrument header line (uppercase).
# Values are the canonical name stored in the result dict.
# The parser matches the FIRST key found anywhere in the header line, so be
# as specific as needed to avoid false positives.
# ──────────────────────────────────────────────────────────────────────────────
TARGET_INSTRUMENTS: Dict[str, str] = {
    # Forex – 7 majors
    "EURO FX - CHICAGO":          "EURO FX",           # EUR/USD  (avoid EURO FX/GBP, EURO FX/JPY)
    "BRITISH POUND":               "BRITISH POUND",     # GBP/USD
    "JAPANESE YEN":                "JAPANESE YEN",      # JPY/USD
    "SWISS FRANC":                 "SWISS FRANC",       # CHF/USD
    "CANADIAN DOLLAR":             "CANADIAN DOLLAR",   # CAD/USD
    "AUSTRALIAN DOLLAR":           "AUSTRALIAN DOLLAR", # AUD/USD
    "NZ DOLLAR":                   "NZ DOLLAR",         # NZD/USD

    # Metals
    "GOLD - COMMODITY EXCHANGE":   "GOLD",              # CMX file  (avoid MICRO GOLD)
    "SILVER - COMMODITY EXCHANGE": "SILVER",            # CMX file

    # Crypto
    "BITCOIN - CHICAGO":           "BITCOIN",           # CME file  (avoid MICRO BITCOIN)
}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — Extract raw <pre> text from the HTML file
# ──────────────────────────────────────────────────────────────────────────────
class _PreExtractor(HTMLParser):
    """Pulls all text inside <pre>…</pre> blocks."""

    def __init__(self):
        super().__init__()
        self._in_pre = False
        self.blocks: List[str] = []
        self._buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self._in_pre = True
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "pre" and self._in_pre:
            self._in_pre = False
            self.blocks.append("".join(self._buf))

    def handle_data(self, data):
        if self._in_pre:
            self._buf.append(data)


def _extract_pre_text(html: str) -> str:
    """Return all <pre> blocks joined as a single string."""
    parser = _PreExtractor()
    parser.feed(html)
    return "\n".join(parser.blocks)


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2 — Split the pre-text into per-instrument blocks
# ──────────────────────────────────────────────────────────────────────────────
# Each instrument block starts with its name line:
#   EURO FX - CHICAGO MERCANTILE EXCHANGE     Code-099741
# The pattern below captures everything up to the next instrument header OR
# end of string.

_INSTRUMENT_HEADER_RE = re.compile(
    r"^([A-Z][^\n]+?-[^\n]+?Code-\S+)",
    re.MULTILINE,
)


def _split_into_blocks(text: str) -> List[Tuple[str, str]]:
    """
    Returns list of (header_line, block_text) tuples.
    block_text includes the header line itself.
    """
    matches = list(_INSTRUMENT_HEADER_RE.finditer(text))
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        header = m.group(1).strip()
        body = text[start:end]
        blocks.append((header, body))
    return blocks


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — Parse one instrument block
# ──────────────────────────────────────────────────────────────────────────────
def _parse_num(s: str) -> int:
    """'  -27,392' → -27392"""
    s = s.strip().replace(",", "")
    return int(s)


def _parse_float(s: str) -> float:
    return float(s.strip())


def _parse_date(raw: str) -> str:
    """'03/17/26' → '2026-03-17'"""
    return datetime.strptime(raw.strip(), "%m/%d/%y").strftime("%Y-%m-%d")


# Regex pieces
_AS_OF_RE      = re.compile(r"AS OF\s+(\d{2}/\d{2}/\d{2})")
_OI_RE         = re.compile(r"OPEN INTEREST:\s*([\d,]+)")
_CODE_RE       = re.compile(r"Code-(\S+)")
_SPEC_RE       = re.compile(r"\(([^)]+)\)\s+OPEN INTEREST")
_CHANGES_RE    = re.compile(
    r"CHANGES FROM\s+(\d{2}/\d{2}/\d{2})\s*\(CHANGE IN OPEN INTEREST:\s*([-\d,]+)\)"
)

# The four data rows each have 9 numbers (some may be negative).
# We capture them as whitespace-separated tokens.
_NUM_PAT = r"([-\s]?[\d,]+)"          # one number token (handles negative)

def _get_9_nums(line: str) -> Optional[List[int]]:
    """Extract exactly 9 integers from a data row, or None if not enough."""
    tokens = re.findall(r"-?[\d,]+", line)
    if len(tokens) < 9:
        return None
    return [_parse_num(t) for t in tokens[:9]]

def _get_9_floats(line: str) -> Optional[List[float]]:
    tokens = re.findall(r"-?[\d.]+", line)
    if len(tokens) < 9:
        return None
    return [_parse_float(t) for t in tokens[:9]]


def _parse_block(header: str, body: str, source_file: str, canonical_name: str) -> Optional[dict]:
    """Parse a single instrument block into a flat dict. Returns None on failure."""
    try:
        result: dict = {}

        result["name"]        = canonical_name
        result["source_file"] = source_file

        # CFTC code
        code_m = _CODE_RE.search(header)
        result["code"] = code_m.group(1) if code_m else ""

        # As-of date
        asof_m = _AS_OF_RE.search(body)
        result["as_of_date"] = _parse_date(asof_m.group(1)) if asof_m else ""

        # Contract spec  e.g. "CONTRACTS OF EUR 125,000"
        spec_m = _SPEC_RE.search(body)
        result["contract_spec"] = spec_m.group(1).strip() if spec_m else ""

        # Open interest
        oi_m = _OI_RE.search(body)
        result["open_interest"] = _parse_num(oi_m.group(1)) if oi_m else 0

        # Prior date + OI change
        chg_m = _CHANGES_RE.search(body)
        if chg_m:
            result["prev_date"] = _parse_date(chg_m.group(1))
            result["oi_change"] = _parse_num(chg_m.group(2))
        else:
            result["prev_date"] = ""
            result["oi_change"] = 0

        # ── Locate the four data rows ──────────────────────────────────────────
        # The block has a fixed structure:
        #   COMMITMENTS
        #   <9 numbers>
        #   CHANGES FROM … (CHANGE IN OPEN INTEREST: …)
        #   <9 numbers>
        #   PERCENT OF OPEN INTEREST FOR EACH CATEGORY OF TRADERS
        #   <9 numbers>
        #   NUMBER OF TRADERS IN EACH CATEGORY (TOTAL TRADERS: …)
        #   <7 numbers + blanks>

        lines = body.splitlines()

        def _find_row_after(keyword: str) -> Optional[str]:
            """Return the first non-blank line that follows 'keyword' in the block."""
            found = False
            for ln in lines:
                if found:
                    stripped = ln.strip()
                    if stripped:
                        return stripped
                if keyword in ln.upper():
                    found = True
            return None

        # Row 1: COMMITMENTS
        commit_line = _find_row_after("COMMITMENTS")
        if not commit_line:
            return None
        c = _get_9_nums(commit_line)
        if not c:
            return None
        (result["nc_long"], result["nc_short"], result["nc_spreads"],
         result["comm_long"], result["comm_short"],
         result["total_long"], result["total_short"],
         result["nr_long"], result["nr_short"]) = c

        # Row 2: CHANGES
        changes_line = _find_row_after("CHANGE IN OPEN INTEREST")
        if not changes_line:
            return None
        ch = _get_9_nums(changes_line)
        if not ch:
            return None
        (result["chg_nc_long"], result["chg_nc_short"], result["chg_nc_spreads"],
         result["chg_comm_long"], result["chg_comm_short"],
         result["chg_total_long"], result["chg_total_short"],
         result["chg_nr_long"], result["chg_nr_short"]) = ch

        # Row 3: PERCENT
        pct_line = _find_row_after("PERCENT OF OPEN INTEREST")
        if not pct_line:
            return None
        pf = _get_9_floats(pct_line)
        if not pf:
            return None
        (result["pct_nc_long"], result["pct_nc_short"], result["pct_nc_spreads"],
         result["pct_comm_long"], result["pct_comm_short"],
         result["pct_total_long"], result["pct_total_short"],
         result["pct_nr_long"], result["pct_nr_short"]) = pf

        # Row 4: NUMBER OF TRADERS
        traders_header = _find_row_after("NUMBER OF TRADERS")
        total_m = re.search(r"TOTAL TRADERS:\s*([\d,]+)", body)
        result["traders_total"] = _parse_num(total_m.group(1)) if total_m else 0

        # Trader row has 7 numbers (NR columns are blank in source)
        traders_line = None
        found_traders = False
        for ln in lines:
            if found_traders:
                stripped = ln.strip()
                if stripped:
                    traders_line = stripped
                    break
            if "NUMBER OF TRADERS" in ln.upper():
                found_traders = True

        if traders_line:
            t_tokens = re.findall(r"[\d,]+", traders_line)
            t = [_parse_num(x) for x in t_tokens[:7]]
            while len(t) < 7:
                t.append(0)
            (result["trd_nc_long"], result["trd_nc_short"], result["trd_nc_spreads"],
             result["trd_comm_long"], result["trd_comm_short"],
             result["trd_total_long"], result["trd_total_short"]) = t
        else:
            for k in ["trd_nc_long","trd_nc_short","trd_nc_spreads",
                      "trd_comm_long","trd_comm_short","trd_total_long","trd_total_short"]:
                result[k] = 0

        return result

    except Exception as exc:
        print(f"  [WARN] Failed to parse '{canonical_name}': {exc}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────
def parse_cot_file(html_path: "Union[str, Path]") -> List[dict]:
    """
    Parse one CFTC COT HTML file and return a list of dicts for the
    target instruments found in that file.

    Parameters
    ----------
    html_path : str or Path
        Path to the downloaded .htm file.

    Returns
    -------
    list[dict]
        One dict per matched instrument (see module docstring for fields).
    """
    path = Path(html_path)
    html = path.read_text(encoding="utf-8", errors="replace")
    source_file = path.name

    pre_text = _extract_pre_text(html)
    if not pre_text.strip():
        # Fallback: some older files wrap everything in <pre> implicitly;
        # treat the whole body as plain text.
        pre_text = html

    blocks = _split_into_blocks(pre_text)
    results = []

    for header, body in blocks:
        header_upper = header.upper()
        matched_name = None

        for key, canonical in TARGET_INSTRUMENTS.items():
            if key.upper() in header_upper:
                matched_name = canonical
                break

        if matched_name is None:
            continue  # not a target instrument

        parsed = _parse_block(header, body, source_file, matched_name)
        if parsed:
            results.append(parsed)
            print(f"  [OK] {matched_name:<22} as_of={parsed['as_of_date']}  OI={parsed['open_interest']:,}")

    return results


def parse_cot_files(html_paths: List) -> List[dict]:
    """
    Parse multiple CFTC COT HTML files and return all matched instruments
    combined into one list.

    Parameters
    ----------
    html_paths : list
        List of file paths. Pass all the files you download each week.
        Duplicates are de-duplicated by (name, as_of_date).

    Returns
    -------
    list[dict]
        Deduplicated list of matched instruments across all files.
    """
    all_results: Dict[tuple, dict] = {}

    for path in html_paths:
        print(f"\nParsing: {path}")
        for record in parse_cot_file(path):
            key = (record["name"], record["as_of_date"])
            if key not in all_results:
                all_results[key] = record
            else:
                print(f"  [SKIP] Duplicate: {record['name']} {record['as_of_date']}")

    return list(all_results.values())


# ──────────────────────────────────────────────────────────────────────────────
# DJANGO INTEGRATION HELPER  (optional — requires Django to be set up)
# ──────────────────────────────────────────────────────────────────────────────
def save_to_django(results: List[dict], model_class) -> int:
    """
    Upsert parsed records into a Django model.

    Your model should have all the fields listed in the module docstring.
    The unique_together (or UniqueConstraint) should be on (name, as_of_date).

    Parameters
    ----------
    results : list[dict]
        Output of parse_cot_files().
    model_class :
        Your Django model class, e.g. CotReport

    Returns
    -------
    int
        Number of records created or updated.
    """
    count = 0
    for rec in results:
        obj, created = model_class.objects.update_or_create(
            name=rec["name"],
            as_of_date=rec["as_of_date"],
            defaults={k: v for k, v in rec.items() if k not in ("name", "as_of_date")},
        )
        count += 1
    return count


# ──────────────────────────────────────────────────────────────────────────────
# UPLOAD VIEW ENTRY-POINT
# Called by the Django view which receives an InMemoryUploadedFile object.
# Accepts the raw HTML text directly instead of a file path on disk.
# ──────────────────────────────────────────────────────────────────────────────
def parse_cot_file_from_text(html_text: str, source_file: str = "upload") -> List[dict]:
    """
    Parse a CFTC COT HTML file that has already been read into memory
    (e.g. from Django's request.FILES) and return matched instruments.

    Parameters
    ----------
    html_text   : str
        Full HTML content as a string — decode the uploaded file before
        calling this function:
            html_text = uploaded_file.read().decode("utf-8", errors="replace")

    source_file : str
        Original filename stored in the DB for traceability,
        e.g. "deacmesf.htm".  Defaults to "upload".

    Returns
    -------
    list[dict]
        One dict per matched target instrument found in the file.
        Dict keys are identical to parse_cot_file() — see module docstring.
    """
    # Extract <pre> text block (same logic as the file-based function)
    pre_text = _extract_pre_text(html_text)

    # Fallback: some older CFTC files have no <pre> tags — treat whole body
    if not pre_text.strip():
        pre_text = html_text

    blocks  = _split_into_blocks(pre_text)
    results: List[dict] = []

    for header, body in blocks:
        header_upper = header.upper()
        matched_name: Optional[str] = None

        for key, canonical in TARGET_INSTRUMENTS.items():
            if key.upper() in header_upper:
                matched_name = canonical
                break

        if matched_name is None:
            continue  # not one of the 10 target instruments

        parsed = _parse_block(header, body, source_file, matched_name)
        if parsed:
            results.append(parsed)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# CLI  — run directly to test:  python cot_parser.py deacmesf.htm deacmxsf.htm
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python cot_parser.py <file1.htm> [file2.htm ...]")
        sys.exit(1)

    records = parse_cot_files(sys.argv[1:])

    print(f"\n{'─'*60}")
    print(f"Total matched instruments: {len(records)}")
    print(f"{'─'*60}")
    print(json.dumps(records, indent=2))