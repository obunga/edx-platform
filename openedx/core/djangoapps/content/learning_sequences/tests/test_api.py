"""
Top level API tests. Tests API public contracts only.
"""
from datetime import datetime, timezone
from itertools import count

from django.test import TestCase
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys.edx.locator import BlockUsageLocator

from ..api.data import (
    CourseOutlineData, CourseItemVisibilityData, CourseSectionData, LearningSequenceData
)
from ..api import (
    get_course_outline, get_course_outline_for_user, replace_course_outline
)


class RoundTripTestCase(TestCase):
    """
    Simple tests to ensure that we can pull back the same data we put in, and
    that we don't break when storing or retrieving edge cases.
    """
    def roundtrip(self, input_outline):
         replace_course_outline(self.course_key, input_outline)
         output_outline = get_course_outline(self.course_key)
         assert input_outline == output_outline

    def make_usage_key(self, block_type):
        return BlockUsageLocator(self.course_key, block_type, next(self.usage_counter))

    def setUp(self):
        self.course_key = CourseKey.from_string("course-v1:openedx+outline+run1")
        self.usage_counter = count()

    def test_simple(self):
        self.roundtrip(
            CourseOutlineData(
                course_key=self.course_key,
                title="My Course",
                published_at=datetime(2020, 3, 21, tzinfo=timezone.utc),
                published_version="v1",
                # sections=

            )
        )
