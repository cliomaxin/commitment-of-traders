from django.db import models


class ExtrapolatedReport(models.Model):
    CATEGORY_CURRENCIES = 'currencies'
    CATEGORY_METALS = 'metals'
    CATEGORY_CRYPTO = 'crypto'

    CATEGORY_CHOICES = [
        (CATEGORY_CURRENCIES, 'Major Currencies'),
        (CATEGORY_METALS, 'Metals'),
        (CATEGORY_CRYPTO, 'Cryptocurrency'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    report_date = models.DateField()
    url = models.URLField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('category', 'report_date')]
        ordering = ['-report_date', 'category']

    def __str__(self):
        return f"{self.get_category_display()} {self.report_date} -> {self.url}"
