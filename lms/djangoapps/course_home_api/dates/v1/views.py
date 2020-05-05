"""
Dates Tab Views
"""


from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.courses import get_course_date_blocks, get_course_with_access

from .serializers import DatesTabSerializer


class DatesTabView(ListAPIView):
    """
    **Use Cases**

        Request details for the Dates Tab

    **Example Requests**

        GET course/{}/api/course_home/v1/dates

    **Response Values**

        Body consists of the following fields:

        * effort: A textual description of the weekly hours of effort expected

    **Parameters:**

        requested_fields (optional) comma separated list:
            If set, then only those fields will be returned.
        username (optional) username to masquerade as (if requesting user is staff)

    **Returns**

        * 200 on success with above fields.
        * 400 if an invalid parameter was sent or the username was not provided
          for an authenticated request.
        * 403 if a user who does not have permission to masquerade as
          another user specifies a username other than their own.
        * 404 if the course is not available or cannot be seen.
    """

    serializer_class = DatesTabSerializer


    def get_queryset(self):
        return None

    def list(self, request, course_key_string):
        course_key = CourseKey.from_string(course_key_string)
        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=False)
        blocks = get_course_date_blocks(course, request.user, request, include_access=True, include_past_dates=True)
        serializer = self.get_serializer(blocks, many=True)
        return Response(serializer.data)
