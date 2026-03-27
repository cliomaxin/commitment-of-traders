from django.contrib import admin
from django.urls import path
from . import views

app_name = "Display_Data"

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('dates/', views.date_list, name='date_list'),
    path('date/<str:date_str>/', views.date_detail, name='date_detail'),
    path('analysis/', views.analysis, name='analysis'),
    path('analysis/historical/', views.analysis_historical, name='analysis_historical'),
]
