"""


"""
from datetime import datetime, timezone
import json
import logging

from django.contrib.auth import get_user_model
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.auth.session.authentication import SessionAuthenticationAllowInactiveUser
from opaque_keys.edx.keys import CourseKey
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
import attr

from openedx.core.lib.api.permissions import IsStaff
from .api.data import ScheduleData, UserCourseOutlineData
from .api import get_user_course_outline_details


User = get_user_model()
log = logging.getLogger(__name__)


class CourseOutlineView(APIView):
    """
    Display all CourseOutline information for a given user.
    """
    # We want to eventually allow unauthenticated users to use this as well...
    authentication_classes = (JwtAuthentication, SessionAuthenticationAllowInactiveUser)

    # For early testing, restrict this to only global staff...
    permission_classes = (IsStaff,)

    class UserCourseOutlineDataSerializer(BaseSerializer):
        """Read-only serializer for CourseOutlineData for this endpoint."""
        def to_representation(self, user_course_outline_details):
            """
            Convert to something DRF knows how to serialize (so no custom types)

            This is intentionally dumb and lists out every field to make API
            additions/changes more obvious.
            """
            schedule = user_course_outline_details.schedule
            user_course_outline = user_course_outline_details.outline
            return {
                "course_key": str(user_course_outline.course_key),
                "username": str(user_course_outline.user.username),
                "title": user_course_outline.title,
                "published_at": user_course_outline.published_at,
                "published_version": user_course_outline.published_version,
                "sections": [
                    {
                        "usage_key": str(section.usage_key),
                        "title": section.title,
                        "sequences": [
                            str(seq.usage_key) for seq in section.sequences
                        ]
                    }
                    for section in user_course_outline.sections
                ],
                "sequences": {
                    str(usage_key): {
                        "usage_key": str(usage_key),
                        "title": seq_data.title,
                    }
                    for usage_key, seq_data in user_course_outline.sequences.items()
                },
                "schedule": {
                    "course_start": schedule.course_start,
                    "course_end": schedule.course_end,
                    "sections": {
                        str(sched_item_data.usage_key): {
                            "usage_key": str(sched_item_data.usage_key),
                            "start": sched_item_data.start,  # can be None
                            "due": sched_item_data.due,      # can be None
                        }
                        for sched_item_data in schedule.sections.values()
                    },
                    "sequences": {
                        str(sched_item_data.usage_key): {
                            "usage_key": str(sched_item_data.usage_key),
                            "start": sched_item_data.start,  # can be None
                            "due": sched_item_data.due,      # can be None
                        }
                        for sched_item_data in schedule.sequences.values()
                    }
                },
                "visibility": {
                    "hide_from_toc": [
                        str(usage_key) for usage_key in user_course_outline.visibility.hide_from_toc
                    ],
                    # There should probably be a staff_info section we move this to...
                    "visible_to_staff_only": [
                        str(usage_key) for usage_key in user_course_outline.visibility.visible_to_staff_only
                    ],
                }
            }

    def get(self, request, course_key_str, format=None):
        """
        Generally, the questions for an item in a Course Outline are:
        1. Is the user allowed to see that it exists at all. (content gating, enrollment)
        2. Is the user allowed to access the sequence pointed at (should there be a link)

        Generally, unless it's excluded by some user partitioning or gating, we
        should always see that something exists, even if we can't access it.
        Because those things have start dates and deadlines and completion information
        and other things that are useful to see in context.

        Types of supplementary information that people might add:
        * Schedule information
        * Content Group / Cohort information?
        * Completion information
        * Estimates
        * some things are hidden after their due date
        """
        # Translate input params and do any substitutions...
        course_key = CourseKey.from_string(course_key_str)
        at_time = datetime.now(timezone.utc)
        user = self._determine_user(request)

        # Grab the user's outline and any supplemental OutlineProcessor info we need...
        user_course_outline_details = get_user_course_outline_details(course_key, user, at_time)
        serializer = self.UserCourseOutlineDataSerializer(user_course_outline_details)
        return Response(serializer.data)

    def _determine_user(self, request):
        # Requesting for a different user (easiest way to test for students)
        # while restricting access to only global staff...
        requested_username = request.GET.get("username")
        if request.user.is_staff and requested_username:
            return User.objects.get(username=requested_username)

        return request.user


