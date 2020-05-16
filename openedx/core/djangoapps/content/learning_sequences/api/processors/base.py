"""
Expectation for all OutlineProcessors are:

* something to do a one-time load of data for an entire course
* a method to call to emit a list of usage_keys to hide
* a method to call to add any data that is relevant to this system.

# Processors that we need:

Attributes that apply to both Sections and Sequences
* start
* .hide_from_toc

Might make sense to put this whole thing as a "private" module in an api package,
with the understanding that it's not part of the external contract yet.
"""
import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey, UsageKey

from ..data import ScheduleData, ScheduleItemData

User = get_user_model()
log = logging.getLogger(__name__)


class OutlineProcessor:
    """

    """
    def __init__(self, course_key: CourseKey, user: User, at_time: datetime):
        """
        Basic initialization.

        Extend to set your own data attributes, but don't do any real work (e.g.
        database access, expensive computation) here.
        """
        self.course_key = course_key
        self.user = user
        self.at_time = at_time

    def load_data(self):
        """
        Fetch whatever data you need about the course and user here.

        DO NOT USE MODULESTORE OR BLOCKSTRUCTURES HERE, as the up-front
        performance penalties of those modules are the entire reason this app
        exists.
        """
        raise NotImplementedError()

    def inaccessible_usage_keys(self, full_course_outline):
        """
        Return a set/frozenset of UsageKeys that are not accessible.

        This will not be run for staff users.
        """
        raise NotImplementedError()

    def usage_keys_to_remove(self, full_course_outline):
        """
        Return a set/frozenset of UsageKeys to remove altogether.

        This should not be run for staff users.
        """
        raise NotImplementedError()

    @classmethod
    def is_sequence(cls, usage_key):
        return usage_key.block_type == 'sequential'

    @classmethod
    def is_section(cls, usage_key):
        return usage_key.block_type == 'chapter'
