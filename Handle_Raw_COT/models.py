"""
models.py  —  cot/models.py
============================
Three models:

  1. ImportLog
     One record per uploaded file. Tracks who uploaded it, when,
     how many instruments were found, created, and updated.

  2. CotReport
     Core model. One row = one instrument + one reporting week.
     Holds every field the parser produces: identity, commitments,
     week-over-week changes, % of open interest, and trader counts.

  3. CotReportHistory  (optional audit trail)
     Snapshot written every time a CotReport row is updated so you
     can see what the numbers were before a re-import overwrote them.

Run after adding to INSTALLED_APPS:
    python manage.py makemigrations cot
    python manage.py migrate
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Choices
# ─────────────────────────────────────────────────────────────────────────────

INSTRUMENT_CHOICES = [
    # Forex — 7 majors
    ("EURO FX",           "Euro FX  (EUR/USD)"),
    ("BRITISH POUND",     "British Pound  (GBP/USD)"),
    ("JAPANESE YEN",      "Japanese Yen  (JPY/USD)"),
    ("SWISS FRANC",       "Swiss Franc  (CHF/USD)"),
    ("CANADIAN DOLLAR",   "Canadian Dollar  (CAD/USD)"),
    ("AUSTRALIAN DOLLAR", "Australian Dollar  (AUD/USD)"),
    ("NZ DOLLAR",         "NZ Dollar  (NZD/USD)"),
    # Metals
    ("GOLD",              "Gold"),
    ("SILVER",            "Silver"),
    # Crypto
    ("BITCOIN",           "Bitcoin"),
]

ASSET_CLASS_MAP = {
    "EURO FX":           "forex",
    "BRITISH POUND":     "forex",
    "JAPANESE YEN":      "forex",
    "SWISS FRANC":       "forex",
    "CANADIAN DOLLAR":   "forex",
    "AUSTRALIAN DOLLAR": "forex",
    "NZ DOLLAR":         "forex",
    "GOLD":              "metal",
    "SILVER":            "metal",
    "BITCOIN":           "crypto",
}

ASSET_CLASS_CHOICES = [
    ("forex",  "Forex"),
    ("metal",  "Metal"),
    ("crypto", "Crypto"),
]

SOURCE_FILE_CHOICES = [
    ("deacmesf.htm", "CME Futures  (deacmesf.htm)"),
    ("deacmxsf.htm", "CMX Futures  (deacmxsf.htm)"),
    ("other",        "Other"),
]


# ─────────────────────────────────────────────────────────────────────────────
# 1.  ImportLog
# ─────────────────────────────────────────────────────────────────────────────

class ImportLog(models.Model):
    """
    One record per uploaded HTML file.
    Created by the upload view before processing begins; updated once done.
    """

    STATUS_CHOICES = [
        ("pending",  "Pending"),
        ("success",  "Success"),
        ("partial",  "Partial  (some errors)"),
        ("failed",   "Failed"),
    ]

    # Who / when
    uploaded_by   = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="cot_imports",
    )
    uploaded_at   = models.DateTimeField(default=timezone.now)

    # File identity
    filename      = models.CharField(max_length=255)
    file_size_kb  = models.PositiveIntegerField(default=0, help_text="Approximate KB")

    # Processing outcome
    status            = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    instruments_found = models.PositiveSmallIntegerField(default=0)
    records_created   = models.PositiveSmallIntegerField(default=0)
    records_updated   = models.PositiveSmallIntegerField(default=0)
    error_detail      = models.TextField(blank=True, help_text="Any parse/save errors")

    completed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering        = ["-uploaded_at"]
        verbose_name    = "Import Log"
        verbose_name_plural = "Import Logs"

    def __str__(self):
        return f"{self.filename}  [{self.status}]  {self.uploaded_at:%Y-%m-%d %H:%M}"

    def mark_complete(self, created: int, updated: int, errors: str = ""):
        self.records_created = created
        self.records_updated = updated
        self.instruments_found = created + updated
        self.error_detail = errors
        self.status = "success" if not errors else ("partial" if (created + updated) > 0 else "failed")
        self.completed_at = timezone.now()
        self.save(update_fields=[
            "records_created", "records_updated", "instruments_found",
            "error_detail", "status", "completed_at",
        ])


# ─────────────────────────────────────────────────────────────────────────────
# 2.  CotReport  —  the main data model
# ─────────────────────────────────────────────────────────────────────────────

class CotReport(models.Model):
    """
    One row = one instrument + one reporting week.

    Column groups mirror the CFTC source exactly:

        Identity / metadata
        ├── name, code, asset_class, contract_spec
        ├── as_of_date, prev_date
        ├── source_file, import_log
        └── open_interest, oi_change

        Commitments  (9 values)
        ├── Non-Commercial : nc_long  nc_short  nc_spreads
        ├── Commercial     : comm_long  comm_short
        ├── Total          : total_long  total_short
        └── Nonreportable  : nr_long  nr_short

        Changes from prior week  (9 values, same layout)
        └── chg_nc_long … chg_nr_short

        Percent of Open Interest  (9 floats, same layout)
        └── pct_nc_long … pct_nr_short

        Number of Traders  (7 values — NR columns blank in source)
        ├── traders_total
        ├── trd_nc_long  trd_nc_short  trd_nc_spreads
        ├── trd_comm_long  trd_comm_short
        └── trd_total_long  trd_total_short

    Computed properties (not stored):
        net_nc_position   — nc_long minus nc_short
        nc_sentiment      — "bullish" | "bearish" | "neutral"
        net_comm_position — comm_long minus comm_short
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    name         = models.CharField(
        max_length=64,
        choices=INSTRUMENT_CHOICES,
        db_index=True,
    )
    code         = models.CharField(
        max_length=20,
        blank=True,
        help_text="CFTC instrument code, e.g. 099741",
    )
    asset_class  = models.CharField(
        max_length=10,
        choices=ASSET_CLASS_CHOICES,
        blank=True,
        db_index=True,
    )
    contract_spec = models.CharField(
        max_length=128,
        blank=True,
        help_text="e.g. CONTRACTS OF EUR 125,000",
    )

    # ── Dates ────────────────────────────────────────────────────────────────
    as_of_date   = models.DateField(
        db_index=True,
        help_text="CFTC report date (Tuesday of the reporting week)",
    )
    prev_date    = models.DateField(
        null=True, blank=True,
        help_text="Prior week date used for change calculations",
    )

    # ── Source tracing ───────────────────────────────────────────────────────
    source_file  = models.CharField(
        max_length=128,
        blank=True,
        help_text="Original filename, e.g. deacmesf.htm",
    )
    import_log   = models.ForeignKey(
        ImportLog,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
        help_text="The upload session that created/updated this row",
    )

    # ── Open Interest ────────────────────────────────────────────────────────
    open_interest = models.BigIntegerField(default=0)
    oi_change     = models.BigIntegerField(
        default=0,
        help_text="Change in open interest from prior week (signed)",
    )

    # ── Commitments ──────────────────────────────────────────────────────────
    # Non-Commercial
    nc_long    = models.BigIntegerField(default=0)
    nc_short   = models.BigIntegerField(default=0)
    nc_spreads = models.BigIntegerField(default=0)

    # Commercial
    comm_long  = models.BigIntegerField(default=0)
    comm_short = models.BigIntegerField(default=0)

    # Total
    total_long  = models.BigIntegerField(default=0)
    total_short = models.BigIntegerField(default=0)

    # Nonreportable
    nr_long  = models.BigIntegerField(default=0)
    nr_short = models.BigIntegerField(default=0)

    # ── Changes from prior week ───────────────────────────────────────────────
    # Non-Commercial changes
    chg_nc_long    = models.BigIntegerField(default=0)
    chg_nc_short   = models.BigIntegerField(default=0)
    chg_nc_spreads = models.BigIntegerField(default=0)

    # Commercial changes
    chg_comm_long  = models.BigIntegerField(default=0)
    chg_comm_short = models.BigIntegerField(default=0)

    # Total changes
    chg_total_long  = models.BigIntegerField(default=0)
    chg_total_short = models.BigIntegerField(default=0)

    # Nonreportable changes
    chg_nr_long  = models.BigIntegerField(default=0)
    chg_nr_short = models.BigIntegerField(default=0)

    # ── Percent of Open Interest ─────────────────────────────────────────────
    # Non-Commercial %
    pct_nc_long    = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_nc_short   = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_nc_spreads = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Commercial %
    pct_comm_long  = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_comm_short = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Total %
    pct_total_long  = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_total_short = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Nonreportable %
    pct_nr_long  = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_nr_short = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # ── Number of Traders ────────────────────────────────────────────────────
    traders_total = models.PositiveIntegerField(default=0)

    # Non-Commercial trader counts
    trd_nc_long    = models.PositiveIntegerField(default=0)
    trd_nc_short   = models.PositiveIntegerField(default=0)
    trd_nc_spreads = models.PositiveIntegerField(default=0)

    # Commercial trader counts
    trd_comm_long  = models.PositiveIntegerField(default=0)
    trd_comm_short = models.PositiveIntegerField(default=0)

    # Total trader counts
    trd_total_long  = models.PositiveIntegerField(default=0)
    trd_total_short = models.PositiveIntegerField(default=0)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Meta ─────────────────────────────────────────────────────────────────
    class Meta:
        # Prevent saving the same instrument twice for the same week
        constraints = [
            models.UniqueConstraint(
                fields=["name", "as_of_date"],
                name="unique_instrument_per_week",
            )
        ]
        ordering = ["-as_of_date", "name"]
        indexes = [
            models.Index(fields=["name", "as_of_date"]),    # primary lookup
            models.Index(fields=["as_of_date"]),             # all instruments for a week
            models.Index(fields=["asset_class", "as_of_date"]),  # filter by asset class
            models.Index(fields=["name", "-as_of_date"]),   # history for one instrument
        ]
        verbose_name = "COT Report"
        verbose_name_plural = "COT Reports"

    def __str__(self):
        return f"{self.get_name_display()}  —  {self.as_of_date}"

    # ── save() override: auto-populate asset_class ────────────────────────────
    def save(self, *args, **kwargs):
        if not self.asset_class and self.name:
            self.asset_class = ASSET_CLASS_MAP.get(self.name, "")
        super().save(*args, **kwargs)

    # ── Computed properties ───────────────────────────────────────────────────
    @property
    def net_nc_position(self) -> int:
        """Non-commercial net (longs − shorts). Positive = net long = bullish bias."""
        return self.nc_long - self.nc_short

    @property
    def net_comm_position(self) -> int:
        """Commercial net (longs − shorts). Commercials are often contrarian hedgers."""
        return self.comm_long - self.comm_short

    @property
    def nc_sentiment(self) -> str:
        """Simple directional label based on non-commercial net position."""
        net = self.net_nc_position
        if net > 0:
            return "bullish"
        elif net < 0:
            return "bearish"
        return "neutral"

    @property
    def nc_long_pct_of_oi(self) -> float:
        """Non-commercial longs as % of open interest (float, not stored)."""
        if not self.open_interest:
            return 0.0
        return round(self.nc_long / self.open_interest * 100, 2)

    @classmethod
    def latest_report_date(cls) -> "models.DateField | None":
        """Return the most recent as_of_date in the table."""
        result = cls.objects.aggregate(d=models.Max("as_of_date"))
        return result["d"]

    @classmethod
    def latest_for_all_instruments(cls):
        """
        Return one QuerySet row per instrument, each at the latest date.
        Efficient single-query approach using the unique constraint.
        """
        latest = cls.latest_report_date()
        if not latest:
            return cls.objects.none()
        return cls.objects.filter(as_of_date=latest).order_by("name")

    @classmethod
    def history_for(cls, instrument_name: str, weeks: int = 52):
        """
        Return up to `weeks` rows for a single instrument, newest first.
        Useful for charting historical net positions.
        """
        return (
            cls.objects
            .filter(name=instrument_name)
            .order_by("-as_of_date")[:weeks]
        )

    @classmethod
    def from_parser_dict(cls, data: dict, import_log=None) -> "CotReport":
        """
        Build (but do NOT save) a CotReport instance from a parser result dict.
        Call .save() or use update_or_create() afterwards.

        Example
        -------
            report = CotReport.from_parser_dict(parsed_record, import_log=log)
            report.save()

        Or in bulk:
            obj, created = CotReport.objects.update_or_create(
                name=data["name"],
                as_of_date=data["as_of_date"],
                defaults=CotReport.defaults_from_dict(data, import_log),
            )
        """
        instance = cls(import_log=import_log)
        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        return instance

    @staticmethod
    def defaults_from_dict(data: dict, import_log=None) -> dict:
        """
        Return the `defaults` dict for update_or_create(), excluding the
        lookup keys (name, as_of_date) and adding import_log.

        Usage
        -----
            obj, created = CotReport.objects.update_or_create(
                name       = data["name"],
                as_of_date = data["as_of_date"],
                defaults   = CotReport.defaults_from_dict(data, log),
            )
        """
        exclude = {"name", "as_of_date"}
        defaults = {k: v for k, v in data.items() if k not in exclude}
        if import_log is not None:
            defaults["import_log"] = import_log
        return defaults


# ─────────────────────────────────────────────────────────────────────────────
# 3.  CotReportHistory  —  audit trail (optional)
# ─────────────────────────────────────────────────────────────────────────────

class CotReportHistory(models.Model):
    """
    Written every time an existing CotReport row is overwritten by a re-import.
    Lets you recover the previous values if needed.

    Enable by calling CotReport.snapshot() from your view before update_or_create().
    """

    report      = models.ForeignKey(
        CotReport,
        on_delete=models.CASCADE,
        related_name="history",
    )
    snapshotted_at = models.DateTimeField(default=timezone.now)
    import_log  = models.ForeignKey(
        ImportLog,
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    # Snapshot the three numeric groups only (identity fields don't change)
    open_interest = models.BigIntegerField(default=0)
    oi_change     = models.BigIntegerField(default=0)

    nc_long    = models.BigIntegerField(default=0)
    nc_short   = models.BigIntegerField(default=0)
    nc_spreads = models.BigIntegerField(default=0)
    comm_long  = models.BigIntegerField(default=0)
    comm_short = models.BigIntegerField(default=0)
    total_long = models.BigIntegerField(default=0)
    total_short= models.BigIntegerField(default=0)
    nr_long    = models.BigIntegerField(default=0)
    nr_short   = models.BigIntegerField(default=0)

    chg_nc_long    = models.BigIntegerField(default=0)
    chg_nc_short   = models.BigIntegerField(default=0)
    chg_nc_spreads = models.BigIntegerField(default=0)
    chg_comm_long  = models.BigIntegerField(default=0)
    chg_comm_short = models.BigIntegerField(default=0)
    chg_total_long = models.BigIntegerField(default=0)
    chg_total_short= models.BigIntegerField(default=0)
    chg_nr_long    = models.BigIntegerField(default=0)
    chg_nr_short   = models.BigIntegerField(default=0)

    pct_nc_long    = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_nc_short   = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_nc_spreads = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_comm_long  = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_comm_short = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_total_long = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_total_short= models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_nr_long    = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pct_nr_short   = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    traders_total   = models.PositiveIntegerField(default=0)
    trd_nc_long     = models.PositiveIntegerField(default=0)
    trd_nc_short    = models.PositiveIntegerField(default=0)
    trd_nc_spreads  = models.PositiveIntegerField(default=0)
    trd_comm_long   = models.PositiveIntegerField(default=0)
    trd_comm_short  = models.PositiveIntegerField(default=0)
    trd_total_long  = models.PositiveIntegerField(default=0)
    trd_total_short = models.PositiveIntegerField(default=0)

    class Meta:
        ordering     = ["-snapshotted_at"]
        verbose_name = "COT Report History"
        verbose_name_plural = "COT Report Histories"

    def __str__(self):
        return f"Snapshot of {self.report}  @  {self.snapshotted_at:%Y-%m-%d %H:%M}"

    @classmethod
    def snapshot(cls, report: CotReport, import_log=None) -> "CotReportHistory":
        """
        Copy current numeric values of a CotReport into a history row and save it.

        Call this BEFORE calling update_or_create() when you want an audit trail:

            existing = CotReport.objects.filter(name=..., as_of_date=...).first()
            if existing:
                CotReportHistory.snapshot(existing, import_log=log)
            # then proceed with update_or_create …
        """
        numeric_fields = [
            f.name for f in CotReport._meta.get_fields()
            if isinstance(f, (
                models.BigIntegerField,
                models.DecimalField,
                models.PositiveIntegerField,
            ))
            and f.name not in ("id",)
        ]
        kwargs = {f: getattr(report, f) for f in numeric_fields if hasattr(report, f)}
        return cls.objects.create(report=report, import_log=import_log, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Admin registration  (paste into cot/admin.py)
# ─────────────────────────────────────────────────────────────────────────────
"""
# cot/admin.py

from django.contrib import admin
from .models import ImportLog, CotReport, CotReportHistory


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display  = ("filename", "status", "instruments_found",
                     "records_created", "records_updated", "uploaded_at")
    list_filter   = ("status",)
    readonly_fields = ("uploaded_at", "completed_at")


@admin.register(CotReport)
class CotReportAdmin(admin.ModelAdmin):
    list_display  = ("name", "asset_class", "as_of_date",
                     "open_interest", "nc_long", "nc_short",
                     "net_nc_position_display", "nc_sentiment")
    list_filter   = ("asset_class", "as_of_date", "name")
    search_fields = ("name", "code")
    readonly_fields = ("created_at", "updated_at", "asset_class")
    ordering      = ("-as_of_date", "name")

    def net_nc_position_display(self, obj):
        return obj.net_nc_position
    net_nc_position_display.short_description = "NC Net"

    def nc_sentiment(self, obj):
        return obj.nc_sentiment
    nc_sentiment.short_description = "Sentiment"


@admin.register(CotReportHistory)
class CotReportHistoryAdmin(admin.ModelAdmin):
    list_display  = ("report", "snapshotted_at", "open_interest")
    readonly_fields = ("snapshotted_at",)
"""