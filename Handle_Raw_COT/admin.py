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