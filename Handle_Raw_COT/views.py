# Compatible with Python 3.7 and all Django versions (2.x, 3.x, 4.x).
#
# Changes from previous version:
#   - request.headers dict-access replaced with request.META fallback
#     (request.headers was added in Django 2.2; META works everywhere)
#   - No f-strings with = (walrus / assignment expressions — Python 3.8+)
#   - All type hints use typing module style (no built-in generics like list[x])
# ─────────────────────────────────────────────────────────────────────────────

from django.shortcuts import render
from django.views import View
from django.http import JsonResponse

from .models import CotReport, ImportLog
from .cot_parser import parse_cot_file_from_text
from .excel_parser import parse_excel_file_from_bytes
from .forms import CotUploadForm


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