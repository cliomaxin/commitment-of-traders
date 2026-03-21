from django.urls import path
from .views import *

app_name = "Handle_Raw_COT"

urlpatterns = [
    path("upload/", CotUploadView.as_view(), name="upload"),
]