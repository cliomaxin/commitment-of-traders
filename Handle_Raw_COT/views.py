# Compatible with Python 3.7 and all Django versions (2.x, 3.x, 4.x).
#
# Changes from previous version:
#   - request.headers dict-access replaced with request.META fallback
#     (request.headers was added in Django 2.2; META works everywhere)
#   - No f-strings with = (walrus / assignment expressions — Python 3.8+)
#   - All type hints use typing module style (no built-in generics like list[x])
# ─────────────────────────────────────────────────────────────────────────────

import requests
import logging
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache

from .models import CotReport, ImportLog, ScrapedCotReport
from .cot_parser import parse_cot_file_from_text
from .excel_parser import parse_excel_file_from_bytes
from .forms import CotUploadForm
from Get_Data.models import ExtrapolatedReport


def _is_ajax(request):
    """
    Detect AJAX / fetch() requests.
    Works on all Django versions — request.headers requires Django 2.2+
    so we fall back to META which is always available.
    """
    # Modern Django 2.2+
    if hasattr(request, "headers"):
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"
    # Fallback for very old Django
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


class CotUploadView(View):
    template_name = "Raw/upload.html"

    # ── GET — render the empty upload form ───────────────────────────────────
    def get(self, request):
        form   = CotUploadForm()
        recent = CotReport.objects.order_by("-as_of_date", "name").select_related("import_log")[:30]
        return render(request, self.template_name, {
            "form":   form,
            "recent": recent,
        })

    # ── POST — receive files, parse, save ────────────────────────────────────
    def post(self, request):
        ajax = _is_ajax(request)

        # ── 1. Collect uploaded files ─────────────────────────────────────
        # ALWAYS use getlist() — form.cleaned_data["files"] only holds one file
        # because MultipleFileInput.value_from_datadict returns a single value
        # to keep Django's FileField validation happy on older versions.
        uploaded_files = request.FILES.getlist("files")

        if not uploaded_files:
            msg = "No files received. Please select at least one .htm file."
            if ajax:
                return JsonResponse({"status": "error", "message": msg}, status=400)
            return render(request, self.template_name, {
                "form":  CotUploadForm(),
                "error": msg,
            })

        # ── 2. Process each file ──────────────────────────────────────────
        results_summary = []
        all_errors      = []
        total_created   = 0
        total_updated   = 0

        for upload in uploaded_files:
            filename = upload.name

            # Extension guard
            html_exts = (".htm", ".html")
            excel_exts = (".xls", ".xlsx", ".xlsb", ".csv", ".ods")
            if not (filename.lower().endswith(html_exts + excel_exts)):
                all_errors.append(
                    "{}: not a supported file type — skipped. Supported: {}".format(
                        filename, ", ".join(html_exts + excel_exts)
                    )
                )
                continue

            # ── 2a. Create an ImportLog entry ─────────────────────────────
            file_size_kb = max(1, upload.size // 1024) if hasattr(upload, "size") else 0

            log = ImportLog.objects.create(
                uploaded_by  = request.user if request.user.is_authenticated else None,
                filename     = filename,
                file_size_kb = file_size_kb,
                status       = "pending",
            )

            # ── 2b. Read bytes → text or keep as bytes ───────────────────────
            try:
                file_bytes = upload.read()
                if filename.lower().endswith((".htm", ".html")):
                    html_text = file_bytes.decode("utf-8", errors="replace")
                else:
                    html_text = None  # for Excel files
            except Exception as exc:
                err_msg = "{}: could not read file — {}".format(filename, exc)
                all_errors.append(err_msg)
                log.mark_complete(created=0, updated=0, errors=err_msg)
                continue

            # ── 2c. Parse ────────────────────────────────────────────────
            try:
                if filename.lower().endswith((".htm", ".html")):
                    records = parse_cot_file_from_text(html_text, source_file=filename)
                else:
                    records = parse_excel_file_from_bytes(file_bytes, filename=filename)
            except Exception as exc:
                err_msg = "{}: parse error — {}".format(filename, exc)
                all_errors.append(err_msg)
                log.mark_complete(created=0, updated=0, errors=err_msg)
                continue

            if not records:
                err_msg = (
                    "{}: no target instruments found. "
                    "For HTML files, make sure you are uploading deacmesf.htm or deacmxsf.htm. "
                    "For Excel files, ensure they contain futures data for the target instruments."
                ).format(filename)
                all_errors.append(err_msg)
                log.mark_complete(created=0, updated=0, errors=err_msg)
                continue

            # ── 2d. Save to database ──────────────────────────────────────
            file_created    = 0
            file_updated    = 0
            file_errors     = []
            file_instruments = []

            for rec in records:
                try:
                    obj, created = CotReport.objects.update_or_create(
                        name       = rec["name"],
                        as_of_date = rec["as_of_date"],
                        defaults   = CotReport.defaults_from_dict(rec, import_log=log),
                    )
                    if created:
                        file_created += 1
                    else:
                        file_updated += 1

                    file_instruments.append({
                        "name":          rec["name"],
                        "as_of_date":    rec["as_of_date"],
                        "open_interest": rec["open_interest"],
                        "nc_long":       rec["nc_long"],
                        "nc_short":      rec["nc_short"],
                        "created":       created,
                    })

                except Exception as exc:
                    file_errors.append(
                        "  {}: DB save failed — {}".format(rec.get("name", "?"), exc)
                    )

            # ── 2e. Update ImportLog ──────────────────────────────────────
            log.mark_complete(
                created = file_created,
                updated = file_updated,
                errors  = "\n".join(file_errors),
            )

            total_created += file_created
            total_updated += file_updated
            all_errors.extend(file_errors)

            results_summary.append({
                "file":        filename,
                "instruments": file_instruments,
                "created":     file_created,
                "updated":     file_updated,
            })

        # ── 3. Build response ─────────────────────────────────────────────
        payload = {
            "status":        "ok" if results_summary else "error",
            "total_created": total_created,
            "total_updated": total_updated,
            "files":         results_summary,
            "errors":        all_errors,
        }

        if ajax:
            return JsonResponse(payload)

        return render(request, self.template_name, {
            "form":    CotUploadForm(),
            "payload": payload,
            "recent":  CotReport.objects.order_by("-as_of_date", "name")[:30],
        })


class ScrapeCotLinksView(View):
    template_name = "Raw/scraping_data.html"

    def get(self, request):
        total_urls = ExtrapolatedReport.objects.count()
        last_log = ImportLog.objects.filter(filename__startswith="remote-urls-scrape").order_by("-uploaded_at").first()
        recent = ScrapedCotReport.objects.order_by("-as_of_date", "name")[:20]
        return render(request, self.template_name, {
            "total_urls": total_urls,
            "last_log": last_log,
            "recent": recent,
        })

    def post(self, request):
        # Enable requests logging
        logging.basicConfig()
        logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.DEBUG)

        urls = list(ExtrapolatedReport.objects.order_by("category", "report_date").values_list("url", flat=True))
        total_urls = len(urls)

        # Generate a unique task ID
        import uuid
        task_id = str(uuid.uuid4())

        # Start scraping in background thread
        thread = threading.Thread(target=self._scrape_urls, args=(task_id, urls, request.user if request.user.is_authenticated else None))
        thread.start()

        # Return immediately with task ID
        return JsonResponse({"task_id": task_id, "total_urls": total_urls})

    def _scrape_urls(self, task_id, urls, user):
        cache.set(f"scrape_progress_{task_id}", {"status": "starting", "current": 0, "total": len(urls), "message": "Initializing scrape..."}, timeout=3600)

        log = ImportLog.objects.create(
            uploaded_by  = user,
            filename     = f"remote-urls-scrape-{timezone.now():%Y%m%d%H%M%S}.txt",
            file_size_kb = 0,
            status       = "pending",
        )

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        })

        created = 0
        updated = 0
        url_results = []
        errors = []

        for i, url in enumerate(urls):
            cache.set(f"scrape_progress_{task_id}", {
                "status": "processing",
                "current": i + 1,
                "total": len(urls),
                "message": f"Processing URL: {url}",
                "url": url
            }, timeout=3600)

            print(f"Processing URL: {url}")
            try:
                response = session.get(url, timeout=20)
                response.raise_for_status()
                html_text = response.text
            except Exception as exc:
                error_text = f"{url}: fetch failed — {exc}"
                errors.append(error_text)
                url_results.append({"url": url, "error": error_text})
                continue

            source_file = Path(urlparse(url).path).name or "remote-report"
            try:
                records = parse_cot_file_from_text(html_text, source_file=source_file)
            except Exception as exc:
                error_text = f"{url}: parse error — {exc}"
                errors.append(error_text)
                url_results.append({"url": url, "error": error_text})
                continue

            if not records:
                error_text = f"{url}: no target instruments found"
                errors.append(error_text)
                url_results.append({"url": url, "error": error_text})
                continue

            created_for_url = 0
            updated_for_url = 0
            for rec in records:
                defaults = ScrapedCotReport.defaults_from_dict(rec, import_log=log)
                _, was_created = ScrapedCotReport.objects.update_or_create(
                    name=rec["name"],
                    as_of_date=rec["as_of_date"],
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                    created_for_url += 1
                else:
                    updated += 1
                    updated_for_url += 1

            url_results.append({
                "url": url,
                "records": len(records),
                "created": created_for_url,
                "updated": updated_for_url,
            })

        log.mark_complete(created=created, updated=updated, errors="\n".join(errors))

        cache.set(f"scrape_progress_{task_id}", {
            "status": "completed",
            "current": len(urls),
            "total": len(urls),
            "message": "Scraping completed",
            "results": {
                "created": created,
                "updated": updated,
                "errors": errors,
                "url_results": url_results,
            }
        }, timeout=3600)


class ScrapeProgressView(View):
    def get(self, request, task_id):
        progress = cache.get(f"scrape_progress_{task_id}")
        if progress:
            return JsonResponse(progress)
        return JsonResponse({"status": "not_found"}, status=404)