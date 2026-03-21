from django.shortcuts import render
from django.db import models
from Handle_Raw_COT.models import CotReport

# Create your views here.
def index(request):
    # Get the latest date
    latest_date = CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).first()
    if latest_date:
        reports = CotReport.objects.filter(as_of_date=latest_date).order_by('name')
    else:
        reports = CotReport.objects.none()
    
    # Get all available dates for navigation
    all_dates = CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).distinct()
    
    return render(request, 'Display/index.html', {
        'reports': reports,
        'instruments_count': reports.count(),
        'latest_date': latest_date,
        'all_dates': all_dates,
    })

def date_list(request):
    # Get all available dates with counts
    dates_with_counts = CotReport.objects.values('as_of_date').annotate(
        count=models.Count('id')
    ).order_by('-as_of_date')
    
    return render(request, 'Display/date_list.html', {
        'dates_with_counts': dates_with_counts,
    })

def date_detail(request, date_str):
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        reports = CotReport.objects.filter(as_of_date=date_obj).order_by('name')
        return render(request, 'Display/index.html', {
            'reports': reports,
            'instruments_count': reports.count(),
            'latest_date': date_obj,
            'all_dates': CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).distinct(),
            'is_historical': True,
        })
    except ValueError:
        # Invalid date format
        return render(request, 'Display/date_list.html', {
            'error': 'Invalid date format',
        })