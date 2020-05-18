import logging
from collections import defaultdict, OrderedDict
from datetime import datetime

from django.contrib.auth import get_user_model
from edx_when.api import get_dates_for_course
from opaque_keys.edx.keys import CourseKey, UsageKey

from ..data import ScheduleData, ScheduleItemData
from .base import OutlineProcessor

User = get_user_model()
log = logging.getLogger(__name__)


class ScheduleOutlineProcessor(OutlineProcessor):
    """

    Things we don't handle yet:
    * Beta test users
    * Self-paced courses
    * Things that are made inaccessible after they're due.
    """

    def __init__(self, course_key: CourseKey, user: User, at_time: datetime):
        super().__init__(course_key, user, at_time)
        self.dates = None
        self.keys_to_schedule_fields = defaultdict(dict)
        self._inaccessible_usage_keys = None
        self._course_start = None
        self._course_end = None

    def load_data(self):
        # (usage_key, 'due'): datetime.datetime(2019, 12, 11, 15, 0, tzinfo=<UTC>)
        self.dates = get_dates_for_course(self.course_key, self.user, outline_only=True)
        for (usage_key, field_name), date in self.dates.items():
            self.keys_to_schedule_fields[usage_key][field_name] = date

        course_usage_key = self.course_key.make_usage_key('course', 'course')
        self._course_start = self.keys_to_schedule_fields[course_usage_key].get('start')
        self._course_end = self.keys_to_schedule_fields[course_usage_key].get('end')

    def usage_keys_to_remove(self, full_course_outline):
        """
        Set of UsageKeys to remove from the CourseOutline.

        We never hide the existence of a piece of content because of start or
        due dates. Content may be inaccessible because it has yet to be released
        or the exam has closed, but students are never prevented from knowing
        the content exists based on the start and due date information.
        """
        return frozenset()

    def inaccessible_sequences(self, full_course_outline):
        """
        Set of UsageKeys for Sequences that are visible, but inaccessible.

        This might include Sequences that have not yet started, or Sequences
        for exams that have closed.
        """
        if self._inaccessible_usage_keys is not None:
            return self._inaccessible_usage_keys

        # If the course hasn't started at all, then everything is inaccessible.
        if self._course_start is None or self.at_time < self._course_start:
            return full_course_outline.sequences

        inaccessible = set()
        for section in full_course_outline.sections:
            section_start = self.keys_to_schedule_fields[section.usage_key].get('start')
            if section_start and self.at_time < section_start:
                # If the section hasn't started yet, all the sequences it
                # contains are inaccessible, regardless of the start value for
                # those sequences.
                inaccessible |= {seq.usage_key for seq in section.sequences}
            else:
                for seq in section.sequences:
                    seq_start = self.keys_to_schedule_fields[seq.usage_key].get('start')
                    if seq_start and self.at_time < seq_start:
                        inaccessible.add(seq.usage_key)

        return inaccessible

    def _effective_start(self, *dates):
        specified_dates = [date for date in dates if date is not None]
        if not specified_dates:
            return None
        return min(specified_dates)

    def schedule_data(self, pruned_course_outline):
        """
        Return the data we want to add to this CourseOutlineData.

        Unlike `hidden_usage_keys`, this method gets a CourseOutlineData
        that only has those LearningSequences that a user has permission to
        access. We can use this to make sure that we're not returning data about
        LearningSequences that the user can't see because it was hidden by a
        different OutlineProcessor.
        """
        pruned_section_keys = {section.usage_key for section in pruned_course_outline.sections}
        course_usage_key = self.course_key.make_usage_key('course', 'course')
        course_start = self.keys_to_schedule_fields[course_usage_key].get('start')
        course_end = self.keys_to_schedule_fields[course_usage_key].get('end')

        sequences = {}
        sections = {}
        for section in pruned_course_outline.sections:
            section_dict = self.keys_to_schedule_fields[section.usage_key]
            section_start = section_dict.get('start')
            section_effective_start = self._effective_start(course_start, section_start)
            section_due = section_dict.get('due')

            sections[section.usage_key] = ScheduleItemData(
                usage_key=section.usage_key,
                start=section_start,
                effective_start=section_effective_start,
                due=section_due,
            )

            for seq in section.sequences:
                seq_dict = self.keys_to_schedule_fields[seq.usage_key]
                seq_start = seq_dict.get('start')
                seq_due = seq_dict.get('due')
                sequences[seq.usage_key] = ScheduleItemData(
                    usage_key=seq.usage_key,
                    start=seq_start,
                    effective_start=self._effective_start(section_effective_start, seq_start),
                    due=seq_due,
                )

        return ScheduleData(
            course_start=course_start,
            course_end=course_end,
            sections=sections,
            sequences=sequences,
        )
