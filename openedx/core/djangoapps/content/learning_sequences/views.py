"""


"""
import json

import attr
from opaque_keys.edx.keys import CourseKey

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from .api import get_course_outline_for_user


class CourseOutlineView(APIView):
    """
    Display all CourseOutline information for a given user.
    """

    class UserCourseOutlineDataSerializer(BaseSerializer):
        """Read-only serializer for CourseOutlineData for this endpoint."""
        def to_representation(self, user_course_outline_data):
            """
            Convert to something DRF knows how to serialize (so no custom types)

            This is intentionally dumb and lists out every field to make API
            additions/changes more obvious.
            """
            course_outline_data = user_course_outline_data.outline
            schedule = user_course_outline_data.schedule
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
                    "visible_to_staff_only": [
                        str(usage_key) for usage_key in course_outline_data.visibility.visible_to_staff_only
                    ],
                }
            }

    def get(self, request, course_key_str, format=None):
        course_key = CourseKey.from_string(course_key_str)
        course_outline_data = get_course_outline_for_user(course_key, request.user)
        serializer = self.UserCourseOutlineDataSerializer(course_outline_data)
        return Response(serializer.data)
