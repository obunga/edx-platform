"""
How to diffentiate between data structures we want to promise as an external
interface vs. internal? Just don't return them? Only export them from api.py?

Note: we're using old-style syntax for attrs because we need to support Python
3.5, but we can move to the PEP-526 style once we move to Python 3.6+.

Note: These attr classes are only allowed to do validation that is entirely
self-contained. They MUST NOT make database calls, network requests, or use API
functions from other apps. This is to keep things easy to reason about.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set #, OrderedDict? Mapping?

import attr
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey, UsageKey


User = get_user_model()
log = logging.getLogger(__name__)


@attr.s(frozen=True)
class LearningSequenceData:
    usage_key = attr.ib(type=UsageKey)
    title = attr.ib(type=str)


@attr.s(frozen=True)
class CourseItemVisibilityData:
    hide_from_toc = attr.ib(type=Set[UsageKey])
    visible_to_staff_only = attr.ib(type=Set[UsageKey])


@attr.s(frozen=True)
class CourseSectionData:
    usage_key = attr.ib(type=UsageKey)
    title = attr.ib(type=str)
    sequences = attr.ib(type=List[LearningSequenceData])


class ObjectDoesNotExist(Exception):
    pass


@attr.s(frozen=True)
class CourseOutlineData:

    class DoesNotExist(ObjectDoesNotExist):
        pass

    course_key = attr.ib(type=CourseKey)

    @course_key.validator
    def not_deprecated(self, attribute, value):
        """
        Only non-deprecated course keys (e.g. course-v1:) are supported.
        The older style of "Org/Course/Run" slash-separated keys will not work.
        """
        if value.deprecated:
            raise ValueError("course_key cannot be a slash-separated course key (.deprecated=True)")

    title = attr.ib(type=str)

    # The time the course was last published. This may be different from the
    # time that the course outline data was generated, since course outline
    # generation happens asynchronously and could be severely delayed by
    # operational issues or bugs that prevent the processing of certain courses.
    published_at = attr.ib(type=datetime)

    # String representation of the version information for a course. There is no
    # guarantee as to what this value is (e.g. a serialization of a BSON
    # ObjectID, a base64 encoding of a BLAKE2 hash, etc.). The only guarantee is
    # that it will change to something different every time the underlying
    # course is modified.
    published_version = attr.ib(type=str)

    #
    sections = attr.ib(type=List[CourseSectionData])

    #@sections.validator
    #def sequences_exist(self, attribute, value):
    #    for seq in value.sequences

    # Note that it's possible for a LearningSequence to appear in sequences and
    # not be in sections, e.g. if the Sequence's hide_from_toc=True
    sequences = attr.ib(type=Dict[UsageKey, LearningSequenceData])

    #
    visibility = attr.ib(type=CourseItemVisibilityData)

    # outline_updated_at


@attr.s(frozen=True)
class ScheduleItemData:
    usage_key = attr.ib(type=UsageKey)
    start = attr.ib(type=Optional[datetime])
    due = attr.ib(type=Optional[datetime])


@attr.s(frozen=True)
class ScheduleData:
    sequences = attr.ib(type=Dict[UsageKey, ScheduleItemData])


@attr.s(frozen=True)
class UserCourseOutlineData:
    """
    A course outline that has been customized for a specific user and time.
    """
    # This is a CourseOutlineData that has been trimmed to only show those
    # things that a user is allowed to know exists. For instance, any sequences
    # that have been marked as `visible_to_staff_only` will not show up in the
    # `outline` for a student.
    outline = attr.ib(type=CourseOutlineData)

    # Django User representing who we've customized this outline for. This may
    # be the AnonymousUser.
    user = attr.ib(type=User)

    # UTC TZ time representing the time for which this user course outline was
    # created. It is possible to create UserCourseOutlineData for a time in the
    # future (i.e. "What will this user be able to see next week?")
    at_time = attr.ib(type=datetime)

    # What Sequences is this `user` allowed to access? Anything in the `outline`
    # is something that the `user` is allowed to know exists, but they might not
    # be able to actually interact with it. For example:
    # * A user might see an exam that has closed, but not be able to access it
    #   any longer.
    # * If anonymous course access is enabled in "public_outline" mode,
    #   unauthenticated users (AnonymousUser) will see the course outline but
    #   not be able to access anything inside.
    accessible_sequences = attr.ib(type=Set[UsageKey])
