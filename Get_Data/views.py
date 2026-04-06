from datetime import date, timedelta
from collections import defaultdict

from django.shortcuts import render

from .models import ExtrapolatedReport

CATEGORY_CONFIG = {
    'currencies': {
        'label': 'Major Currencies',
        'start_date': date(2005, 1, 4),
        'prefix': 'deacmesf',
        'subdir': 'futures',
    },
    'metals': {
        'label': 'Metals',
        'start_date': date(2005, 1, 4),
        'prefix': 'deacmetf',
        'subdir': 'futures',
    },
    'crypto': {
        'label': 'Bitcoin (Cryptocurrency)',
        'start_date': date(2017, 12, 26),
        'prefix': 'deacbtc',
        'subdir': 'futures',
    },
}


def _get_latest_tuesday(from_date: date) -> date:
    diff = (from_date.weekday() - 1) % 7
    return from_date - timedelta(days=diff)


def _normalize_tuesday(d: date) -> date:
    while d.weekday() != 1:
        d += timedelta(days=1)
    return d


def extrapolate_dates(request):
    message = ''
    generated = []

    if request.method == 'POST':
        category = request.POST.get('category')
        config = CATEGORY_CONFIG.get(category)

        if config:
            start = _normalize_tuesday(config['start_date'])
            end = _get_latest_tuesday(date.today())
            current = start
            while current <= end:
                code_suffix = current.strftime('%m%d%y')
                report_url = (
                    f"https://www.cftc.gov/sites/default/files/files/dea/cotarchives/{current.year}/{config['subdir']}/{config['prefix']}{code_suffix}.htm"
                )
                _, created = ExtrapolatedReport.objects.get_or_create(
                    category=category,
                    report_date=current,
                    defaults={'url': report_url},
                )
                if created:
                    generated.append(report_url)
                current += timedelta(days=7)

            message = (
                f"{len(generated)} URLs generated and upserted for {config['label']} "
                f"({start.isoformat()} → {end.isoformat()})."
            )
        else:
            message = 'Unknown category selected.'

    # Build grouped and year-organized data for each category
    grouped_reports = []
    for key, config in CATEGORY_CONFIG.items():
        reports = ExtrapolatedReport.objects.filter(category=key).order_by('-report_date')
        
        # Group reports by year
        years_dict = defaultdict(list)
        for report in reports:
            year = report.report_date.year
            years_dict[year].append(report)
        
        # Sort years in descending order
        sorted_years = sorted(years_dict.keys(), reverse=True)
        
        year_groups = []
        for year in sorted_years:
            year_reports = sorted(years_dict[year], key=lambda r: r.report_date, reverse=True)
            year_groups.append({
                'year': year,
                'count': len(year_reports),
                'reports': year_reports,
            })
        
        grouped_reports.append({
            'key': key,
            'label': config['label'],
            'year_groups': year_groups,
            'total_count': len(reports),
        })

    return render(
        request,
        'Get_Data/extrapolate_dates.html',
        {
            'category_config': CATEGORY_CONFIG,
            'grouped_reports': grouped_reports,
            'message': message,
            'generated': generated,
        },
    )
