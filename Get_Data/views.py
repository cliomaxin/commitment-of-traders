from datetime import date, timedelta

from django.shortcuts import render

from .models import ExtrapolatedReport

CATEGORY_CONFIG = {
    'currencies': {
        'label': 'Major Currencies',
        'start_date': date(1986, 1, 15),
        'prefix': 'deacmesf',
        'subdir': 'futures',
    },
    'metals': {
        'label': 'Metals',
        'start_date': date(1986, 1, 15),
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


def _get_latest_wednesday(from_date: date) -> date:
    diff = (from_date.weekday() - 2) % 7
    return from_date - timedelta(days=diff)


def _normalize_wednesday(d: date) -> date:
    while d.weekday() != 2:
        d += timedelta(days=1)
    return d


def extrapolate_dates(request):
    message = ''
    generated = []

    if request.method == 'POST':
        category = request.POST.get('category')
        config = CATEGORY_CONFIG.get(category)

        if config:
            start = _normalize_wednesday(config['start_date'])
            end = _get_latest_wednesday(date.today())
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

    # Keep unsliced base queryset so we can apply per-category filtering safely.
    grouped = [
        {
            'key': key,
            'label': config['label'],
            'reports': ExtrapolatedReport.objects.filter(category=key).order_by('-report_date')[:200],
        }
        for key, config in CATEGORY_CONFIG.items()
    ]

    return render(
        request,
        'Get_Data/extrapolate_dates.html',
        {
            'category_config': CATEGORY_CONFIG,
            'grouped_reports': grouped,
            'message': message,
            'generated': generated,
        },
    )
