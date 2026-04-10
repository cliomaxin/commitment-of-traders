from django.shortcuts import render
from .models import HistoricalCotReport
from collections import defaultdict
from datetime import datetime

def history(request):
    # Fetch all reports and organize by category and year
    all_reports = HistoricalCotReport.objects.all().order_by('-report_date')

    # Group reports by category, then by year
    organized_data = {}

    for category_key, category_label in HistoricalCotReport.CATEGORY_CHOICES:
        category_reports = all_reports.filter(category=category_key)

        if category_reports.exists():
            # Group by year
            years_data = defaultdict(list)

            for report in category_reports:
                year = report.year
                years_data[year].append(report)

            # Sort years in descending order and create a list of year objects
            sorted_years = sorted(years_data.keys(), reverse=True)
            years_list = []
            for year in sorted_years:
                years_list.append({
                    'year': year,
                    'reports': sorted(years_data[year], key=lambda r: r.report_date, reverse=True),
                    'count': len(years_data[year])
                })

            organized_data[category_key] = {
                'label': category_label,
                'years': years_list
            }

    # Get date range for hero sub
    min_year = None
    max_year = None
    if all_reports.exists():
        dates = [r.year for r in all_reports]
        min_year = min(dates) if dates else None
        max_year = max(dates) if dates else None

    context = {
        'organized_data': organized_data,
        'total_urls': all_reports.count(),
        'is_dynamic': True,
    }

    if min_year and max_year:
        context['year_range'] = f"{min_year} → {max_year}"

    return render(request, 'Historical/historical.html', context)