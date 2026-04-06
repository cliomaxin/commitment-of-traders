Run this on terminal first: 

python manage.py shell

from Get_Data.models import ExtrapolatedReport

ExtrapolatedReport.objects.all().delete()