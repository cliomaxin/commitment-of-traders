from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.index, name='index'),
    path('dates/', views.date_list, name='date_list'),
    path('date/<str:date_str>/', views.date_detail, name='date_detail'),
]
