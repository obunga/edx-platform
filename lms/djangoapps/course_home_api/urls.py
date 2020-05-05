"""
Contains all the URLs for the Course Home
"""


from django.conf import settings
from django.urls import re_path

from lms.djangoapps.course_home_api.dates.v1 import views

urlpatterns = []

# Dates Tab URLs
urlpatterns += [
    re_path(r'^course/{}/api/course_home/v1/dates'.format(settings.COURSE_KEY_PATTERN),
        views.DatesTabView.as_view(),
        name="course-home-dates-tab"),
]
