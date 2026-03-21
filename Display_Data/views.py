from django.shortcuts import render
from Handle_Raw_COT.models import CotReport

# Create your views here.
def index(request):
    reports = CotReport.objects.order_by('-as_of_date', 'name').all()
    latest_date = reports.first().as_of_date if reports else None
    return render(request, 'Display/index.html', {
        'reports': reports,
        'instruments_count': reports.count(),
        'latest_date': latest_date,
    })