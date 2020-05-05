"""
Dates Tab Views
"""


from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from edx_django_utils import monitoring as monitoring_utils
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.context_processor import user_timezone_locale_prefs
from lms.djangoapps.courseware.courses import get_course_date_blocks, get_course_with_access
from lms.djangoapps.courseware.date_summary import verified_upgrade_deadline_link
from openedx.core.djangoapps.enrollments.api import get_enrollment

from .serializers import DatesTabSerializer


class DatesTabView(RetrieveAPIView):
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


    def get(self, request, course_key_string):
        course_key = CourseKey.from_string(course_key_string)
        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=False)
        blocks = get_course_date_blocks(course, request.user, request, include_access=True, include_past_dates=True)

        # Enable NR tracing for this view based on course
        monitoring_utils.set_custom_metric('course_id', course_key_string)
        monitoring_utils.set_custom_metric('user_id', request.user.id)
        monitoring_utils.set_custom_metric('is_staff', request.user.is_staff)

        learner_is_verified = False
        enrollment = get_enrollment(request.user.username, course_key_string)
        if enrollment:
            learner_is_verified = enrollment.get('mode') == 'verified'

        # User locale settings
        user_timezone_locale = user_timezone_locale_prefs(request)
        user_timezone = user_timezone_locale['user_timezone']
        user_language = user_timezone_locale['user_language']

        data = {
            'course_number': course.display_number_with_default,
            'course_date_blocks': blocks,
            'verified_upgrade_link': verified_upgrade_deadline_link(request.user, course=course),
            'learner_is_verified': learner_is_verified,
            'user_timezone': user_timezone,
            'user_language': user_language,
        }
        serializer = self.get_serializer(data)


        return Response(serializer.data)
