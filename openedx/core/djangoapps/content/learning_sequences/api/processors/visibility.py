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


class VisibilityOutlineProcessor(OutlineProcessor):
    """
    """

    def load_data(self):
        """No-op, because everything we need is in the CourseOutlineData"""
        pass

    def usage_keys_to_remove(self, full_course_outline):
        """
        Set of UsageKeys to remove from the CourseOutline.
        """
        sections_to_remove = {
            sec.usage_key
            for sec in full_course_outline.sections
            if sec.visibility.hide_from_toc or sec.visibility.visible_to_staff_only
        }
        seqs_to_remove = {
            seq.usage_key
            for seq in full_course_outline.sequences.values()
            if seq.visibility.hide_from_toc or seq.visibility.visible_to_staff_only
        }

        return frozenset(sections_to_remove | seqs_to_remove)

    def inaccessible_sequences(self, full_course_outline):
        return frozenset()
