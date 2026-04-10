from django.db import models
from django.utils import timezone


class HistoricalCotReport(models.Model):
    """
    Model for storing historical COT reports organized by category and year.
    This model is designed specifically for the historical data tree display.
    """

    # Categories matching the static HTML structure
    CATEGORY_FOREX = 'forex'
    CATEGORY_METALS = 'metals'
    CATEGORY_CRYPTO = 'crypto'

    CATEGORY_CHOICES = [
        (CATEGORY_FOREX, 'Forex Major Pairs'),
        (CATEGORY_METALS, 'Precious Metals'),
        (CATEGORY_CRYPTO, 'Cryptocurrencies'),
    ]

    # Core fields
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    report_date = models.DateField(db_index=True)
    url = models.URLField(max_length=512)

    # Metadata
    year = models.PositiveIntegerField(db_index=True)  # Extracted from report_date for easier querying
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('category', 'report_date')]
        ordering = ['category', '-report_date']
        indexes = [
            models.Index(fields=['category', 'year']),
            models.Index(fields=['year', '-report_date']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.report_date}"

    def save(self, *args, **kwargs):
        # Auto-extract year from report_date
        if self.report_date:
            self.year = self.report_date.year
        super().save(*args, **kwargs)

    @classmethod
    def import_from_extrapolated_reports(cls):
        """
        Import all data from Get_Data.ExtrapolatedReport into this model.
        This method handles the data migration.
        """
        from Get_Data.models import ExtrapolatedReport

        imported_count = 0
        updated_count = 0

        for ext_report in ExtrapolatedReport.objects.all():
            # Map category names
            category_mapping = {
                'currencies': cls.CATEGORY_FOREX,
                'metals': cls.CATEGORY_METALS,
                'crypto': cls.CATEGORY_CRYPTO,
            }

            category = category_mapping.get(ext_report.category, ext_report.category)

            # Create or update record
            obj, created = cls.objects.update_or_create(
                category=category,
                report_date=ext_report.report_date,
                defaults={
                    'url': ext_report.url,
                    'year': ext_report.report_date.year,
                }
            )

            if created:
                imported_count += 1
            else:
                updated_count += 1

        return imported_count, updated_count

    @classmethod
    def get_category_stats(cls):
        """
        Get statistics for each category including year counts.
        """
        from django.db.models import Count

        stats = {}
        for category_key, category_label in cls.CATEGORY_CHOICES:
            category_reports = cls.objects.filter(category=category_key)
            year_counts = category_reports.values('year').annotate(
                count=Count('id')
            ).order_by('-year')

            stats[category_key] = {
                'label': category_label,
                'total_reports': category_reports.count(),
                'years': list(year_counts),
            }

        return stats
