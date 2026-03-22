from django.urls import path
from . import views

app_name = "Historical_Data"

urlpatterns = [
    path('historical/', views.history, name='historical'),
]
