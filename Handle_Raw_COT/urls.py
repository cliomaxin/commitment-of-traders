from django.urls import path
from .views import *

app_name = "Handle_Raw_COT"

urlpatterns = [
    path("upload/", CotUploadView.as_view(), name="upload"),
    path("scraping/", ScrapeCotLinksView.as_view(), name="scraping"),
    path("scraping/progress/<str:task_id>/", ScrapeProgressView.as_view(), name="scraping_progress"),
]