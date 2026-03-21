import io
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt  # remove if using {% csrf_token %}
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User, auth
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import CotReport
from .cot_parser import parse_cot_file_from_text
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