# ══════════════════════════════════════════════════════════════════════════════
# FILE STRUCTURE — place these in your Django app (e.g. "cot" app)
#
#   cot/
#   ├── views.py           ← this file (views section)
#   ├── urls.py            ← this file (urls section)
#   ├── forms.py           ← this file (forms section)
#   ├── models.py          ← from django_cot_integration.py (previous file)
#   ├── cot_parser.py      ← the parser (previous file, copy here)
#   └── templates/
#       └── cot/
#           └── upload.html  ← the HTML file (separate file below)
#
# In your project urls.py add:
#   path("cot/", include("cot.urls")),
# ══════════════════════════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────────────────────────
# forms.py
# ─────────────────────────────────────────────────────────────────────────────
"""
# cot/forms.py

from django import forms


class CotUploadForm(forms.Form):
    files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"multiple": True}),
        label="CFTC HTML Files",
        help_text="Select one or more downloaded CFTC .htm files (e.g. deacmesf.htm, deacmxsf.htm)",
    )

    def clean_files(self):
        # Django only exposes the last file through cleaned_data["files"]
        # when multiple=True — we handle all files in the view via request.FILES.getlist()
        # This clean just validates the single file Django sees.
        f = self.cleaned_data["files"]
        name = f.name.lower()
        if not (name.endswith(".htm") or name.endswith(".html")):
            raise forms.ValidationError("Only .htm / .html files are accepted.")
        return f
"""


# ─────────────────────────────────────────────────────────────────────────────
# views.py
# ─────────────────────────────────────────────────────────────────────────────
"""
# cot/views.py

import io
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt  # remove if using {% csrf_token %}

from .models import CotReport
from .cot_parser import parse_cot_file_from_text   # updated parser (see below)
from .forms import CotUploadForm


class CotUploadView(View):
    template_name = "cot/upload.html"

    def get(self, request):
        form = CotUploadForm()
        recent = CotReport.objects.order_by("-as_of_date", "name")[:20]
        return render(request, self.template_name, {"form": form, "recent": recent})

    def post(self, request):
        # Support both standard form POST and fetch() / AJAX POST
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        uploaded_files = request.FILES.getlist("files")

        if not uploaded_files:
            msg = "No files received."
            if is_ajax:
                return JsonResponse({"status": "error", "message": msg}, status=400)
            form = CotUploadForm()
            return render(request, self.template_name, {"form": form, "error": msg})

        results_summary = []
        all_errors      = []
        total_created   = 0
        total_updated   = 0

        for upload in uploaded_files:
            filename = upload.name

            # Validate extension
            if not (filename.lower().endswith(".htm") or filename.lower().endswith(".html")):
                all_errors.append(f"{filename}: not an .htm/.html file, skipped.")
                continue

            # Read the uploaded bytes as text
            try:
                html_text = upload.read().decode("utf-8", errors="replace")
            except Exception as e:
                all_errors.append(f"{filename}: could not read file — {e}")
                continue

            # Parse
            try:
                records = parse_cot_file_from_text(html_text, source_file=filename)
            except Exception as e:
                all_errors.append(f"{filename}: parse error — {e}")
                continue

            if not records:
                all_errors.append(f"{filename}: no target instruments found.")
                continue

            # Save to database
            file_created = file_updated = 0
            file_instruments = []

            for rec in records:
                obj, created = CotReport.objects.update_or_create(
                    name=rec["name"],
                    as_of_date=rec["as_of_date"],
                    defaults={k: v for k, v in rec.items()
                              if k not in ("name", "as_of_date")},
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

            total_created += file_created
            total_updated += file_updated

            results_summary.append({
                "file":        filename,
                "instruments": file_instruments,
                "created":     file_created,
                "updated":     file_updated,
            })

        payload = {
            "status":        "ok" if results_summary else "error",
            "total_created": total_created,
            "total_updated": total_updated,
            "files":         results_summary,
            "errors":        all_errors,
        }

        if is_ajax:
            return JsonResponse(payload)

        return render(request, self.template_name, {
            "form":    CotUploadForm(),
            "payload": payload,
        })
"""


# ─────────────────────────────────────────────────────────────────────────────
# urls.py
# ─────────────────────────────────────────────────────────────────────────────
"""
# cot/urls.py

from django.urls import path
from .views import CotUploadView

app_name = "cot"

urlpatterns = [
    path("upload/", CotUploadView.as_view(), name="upload"),
]
"""


# ─────────────────────────────────────────────────────────────────────────────
# Updated cot_parser.py — add this one function to the existing parser file
# so the view can call it with raw text instead of a file path.
# ─────────────────────────────────────────────────────────────────────────────
"""
# Add to cot/cot_parser.py  (alongside the existing parse_cot_file function)

def parse_cot_file_from_text(html_text: str, source_file: str = "upload") -> list[dict]:
    \"\"\"
    Same as parse_cot_file() but accepts raw HTML text instead of a file path.
    Used by the Django upload view which receives InMemoryUploadedFile objects.

    Parameters
    ----------
    html_text   : str   — full HTML content already read into memory
    source_file : str   — filename label stored in the DB (for traceability)
    \"\"\"
    pre_text = _extract_pre_text(html_text)
    if not pre_text.strip():
        pre_text = html_text          # fallback for plain-text files

    blocks  = _split_into_blocks(pre_text)
    results = []

    for header, body in blocks:
        header_upper = header.upper()
        matched_name = None

        for key, canonical in TARGET_INSTRUMENTS.items():
            if key.upper() in header_upper:
                matched_name = canonical
                break

        if matched_name is None:
            continue

        parsed = _parse_block(header, body, source_file, matched_name)
        if parsed:
            results.append(parsed)

    return results
"""
