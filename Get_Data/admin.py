from django.contrib import admin

from .models import ExtrapolatedReport


@admin.register(ExtrapolatedReport)
class ExtrapolatedReportAdmin(admin.ModelAdmin):
    list_display  = ("category", "report_date", "url", "created_at")
    list_filter   = ("category", "report_date")
    search_fields = ("url", "category")
    readonly_fields = ("created_at",)
    ordering      = ("-report_date", "category")
