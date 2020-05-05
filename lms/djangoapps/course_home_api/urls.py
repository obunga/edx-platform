"""
Contains all the URLs for the Course Home
"""


from django.conf import settings
from django.urls import re_path

from .dates.v1 import views

urlpatterns = []

# Dates Tab URLs
urlpatterns += [
    re_path(r'course_home/v1/dates', views.DatesTabView.as_view(), name="course-home-dates-tab"),
]
