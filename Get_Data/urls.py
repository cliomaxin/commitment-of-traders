from django.urls import path
from . import views

app_name = 'Get_Data'

urlpatterns = [
    path('extrapolate/', views.extrapolate_dates, name='extrapolate_dates'),
    path('update-latest/', views.update_to_latest, name='update_to_latest'),
]
