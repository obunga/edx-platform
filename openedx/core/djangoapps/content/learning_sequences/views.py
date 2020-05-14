"""


"""
from datetime import datetime, timezone
import json

from opaque_keys.edx.keys import CourseKey
import attr

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from .api.data import ScheduleData, UserCourseOutlineData
from .api import get_user_course_outline


class CourseOutlineView(APIView):
    """
    Display all CourseOutline information for a given user.
    """

    class UserCourseOutlineDataSerializer(BaseSerializer):
        """Read-only serializer for CourseOutlineData for this endpoint."""
        def to_representation(self, outline_response_data):
            """
            Convert to something DRF knows how to serialize (so no custom types)

            This is intentionally dumb and lists out every field to make API
            additions/changes more obvious.
            """
            schedule = outline_response_data.schedule
            user_course_outline = outline_response_data.user_course_outline
            course_outline_data = user_course_outline.outline
            return {
                "course_key": str(course_outline_data.course_key),
                "title": course_outline_data.title,
                "published_at": course_outline_data.published_at,
                "published_version": course_outline_data.published_version,
                "sections": [
                    {
                        "usage_key": str(section.usage_key),
                        "title": section.title,
                        "sequences": [
                            str(seq.usage_key) for seq in section.sequences
                        ]
                    }
                    for section in course_outline_data.sections
                ],
                "sequences": {
                    str(usage_key): {
                        "usage_key": str(usage_key),
                        "title": seq_data.title,
                    }
                    for usage_key, seq_data in course_outline_data.sequences.items()
                },
                "schedule": {
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
                        str(usage_key) for usage_key in course_outline_data.visibility.hide_from_toc
                    ],
                    # There should probably be a staff_info section we move this to...
                    "visible_to_staff_only": [
                        str(usage_key) for usage_key in course_outline_data.visibility.visible_to_staff_only
                    ],
                }
            }


    @attr.s(frozen=True)
    class OutlineResponseData:
        user_course_outline = attr.ib(type=UserCourseOutlineData)
        schedule = attr.ib(type=ScheduleData)


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

        # Grab the user's outline and any supplemental OutlineProcessor info we need...
        user_course_outline, processors = get_user_course_outline(course_key, request.user, at_time)
        schedule_processor = processors['schedule']

        # Assemble our response data...
        response_data = self.OutlineResponseData(
            user_course_outline=user_course_outline,
            schedule=schedule_processor.schedule_data(user_course_outline.outline),
        )
        serializer = self.UserCourseOutlineDataSerializer(response_data)
        return Response(serializer.data)
