from django.shortcuts import render, redirect
from django.db import models
from Handle_Raw_COT.models import CotReport

# Create your views here.

def get_nav_items():
    return [
        {'url': '/', 'label': 'Recent COT'},
        {'url': '/dates/', 'label': 'Historical COT Tabled'},
        {'url': '/analysis/', 'label': 'Recent COT Analysis'},
        {'url': '/signals/', 'label': 'Historical COT Tree'},
        {'url': '/donate/', 'label': 'Import COT'},
    ]

def index(request):
    # Get the latest date
    latest_date = CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).first()
    if latest_date:
        reports = CotReport.objects.filter(as_of_date=latest_date).order_by('name')
    else:
        reports = CotReport.objects.none()
    
    # Get all available dates for navigation
    all_dates = CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).distinct()
    
    # Navigation items
    nav_items = get_nav_items()
    
    return render(request, 'Display/index.html', {
        'reports': reports,
        'instruments_count': reports.count(),
        'latest_date': latest_date,
        'all_dates': all_dates,
        'nav_items': nav_items,
    })

def date_list(request):
    # Get all available dates with counts
    dates_with_counts = CotReport.objects.values('as_of_date').annotate(
        count=models.Count('id')
    ).order_by('-as_of_date')
    
    # Navigation items
    nav_items = get_nav_items()
    
    return render(request, 'Display/date_list.html', {
        'dates_with_counts': dates_with_counts,
        'nav_items': nav_items,
    })

def date_detail(request, date_str):
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        reports = CotReport.objects.filter(as_of_date=date_obj).order_by('name')
        
        # Navigation items
        nav_items = get_nav_items()
        
        return render(request, 'Display/index.html', {
            'reports': reports,
            'instruments_count': reports.count(),
            'latest_date': date_obj,
            'all_dates': CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).distinct(),
            'is_historical': True,
            'nav_items': nav_items,
        })
    except ValueError:
        # Invalid date format
        return render(request, 'Display/date_list.html', {
            'error': 'Invalid date format',
        })

def analysis(request):
    # Get the latest date
    latest_date = CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).first()
    if latest_date:
        reports = CotReport.objects.filter(as_of_date=latest_date).order_by('name')
    else:
        reports = CotReport.objects.none()
    
    # Determine signals for each report
    for report in reports:
        if report.asset_class == 'forex':
            if report.nc_long > report.nc_short and report.comm_short > report.comm_long:
                report.signal = 'Buying'
                report.signal_color = 'green'
            elif report.nc_short > report.nc_long and report.comm_long > report.comm_short:
                report.signal = 'Selling'
                report.signal_color = 'red'
            else:
                report.signal = 'Confused'
                report.signal_color = 'orange'
        elif report.asset_class in ['metal', 'crypto']:
            if report.comm_long > report.comm_short and report.nc_short > report.nc_long:
                report.signal = 'Buying'
                report.signal_color = 'green'
            elif report.comm_short > report.comm_long and report.nc_long > report.nc_short:
                report.signal = 'Selling'
                report.signal_color = 'red'
            else:
                report.signal = 'Confused'
                report.signal_color = 'orange'
        else:
            report.signal = 'Confused'
            report.signal_color = 'orange'
    
    # Create summary lists
    buying = [report.get_name_display() for report in reports if report.signal == 'Buying']
    confused = [report.get_name_display() for report in reports if report.signal == 'Confused']
    selling = [report.get_name_display() for report in reports if report.signal == 'Selling']
    
    # Get all available dates for navigation
    all_dates = CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).distinct()
    
    # Navigation items
    nav_items = get_nav_items()
    
    return render(request, 'Display/analysis.html', {
        'reports': reports,
        'instruments_count': reports.count(),
        'latest_date': latest_date,
        'all_dates': all_dates,
        'buying': buying,
        'confused': confused,
        'selling': selling,
        'nav_items': nav_items,
    })

def analysis_historical(request):
    # Get all available dates with analysis summaries
    dates_with_analysis = []
    
    all_dates = CotReport.objects.order_by('-as_of_date').values_list('as_of_date', flat=True).distinct()
    
    for date in all_dates:
        reports = CotReport.objects.filter(as_of_date=date).order_by('name')
        
        # Determine signals for each report
        buying = []
        confused = []
        selling = []
        
        for report in reports:
            if report.asset_class == 'forex':
                if report.nc_long > report.nc_short and report.comm_short > report.comm_long:
                    buying.append(report.get_name_display())
                elif report.nc_short > report.nc_long and report.comm_long > report.comm_short:
                    selling.append(report.get_name_display())
                else:
                    confused.append(report.get_name_display())
            elif report.asset_class in ['metal', 'crypto']:
                if report.comm_long > report.comm_short and report.nc_short > report.nc_long:
                    buying.append(report.get_name_display())
                elif report.comm_short > report.comm_long and report.nc_long > report.nc_short:
                    selling.append(report.get_name_display())
                else:
                    confused.append(report.get_name_display())
            else:
                confused.append(report.get_name_display())
        
        dates_with_analysis.append({
            'date': date,
            'count': reports.count(),
            'buying': buying,
            'confused': confused,
            'selling': selling,
        })
    
    # Navigation items
    nav_items = get_nav_items()
    
    return render(request, 'Display/analysis_historical.html', {
        'dates_with_analysis': dates_with_analysis,
        'nav_items': nav_items,
    })


def signals_redirect(request):
    return redirect('Historical_Data:historical')


def donate_redirect(request):
    return redirect('Handle_Raw_COT:upload')

