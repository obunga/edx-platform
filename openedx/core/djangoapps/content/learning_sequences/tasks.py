import json
import logging
import pprint
from collections import OrderedDict

from celery.task import task
from django.db import transaction
from django.dispatch import receiver
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore, SignalHandler

from .api import replace_course_outline
from .api.data import (
    CourseOutlineData, CourseItemVisibilityData, CourseSectionData, LearningSequenceData
)


@receiver(SignalHandler.course_published)
def ls_listen_for_course_publish(sender, course_key, **kwargs):
    # update_from_modulestore.delay(course_key)
    return

    if not isinstance(course_key, CourseKey):
        return
    if course_key.deprecated:
        return
    update_from_modulestore(course_key)


log = logging.getLogger(__name__)


def update_from_modulestore(course_key):
    """
    Should this live in another system as a post-publish hook to push data to
    the LMS?
    """
    def _make_section_data(section):
        hide_from_toc_set = set()
        visible_to_staff_only_set = set()

        if section.hide_from_toc:
            hide_from_toc_set.add(section.location)
        if section.visible_to_staff_only:
            visible_to_staff_only_set.add(section.location)

        sequences_data = []
        for sequence in section.get_children():
            sequences_data.append(
                LearningSequenceData(
                    usage_key=sequence.location,
                    title=sequence.display_name,
                )
            )
            if sequence.hide_from_toc:
                hide_from_toc_set.add(sequence.location)
            if sequence.visible_to_staff_only:
                visible_to_staff_only_set.add(sequence.location)

        section_data = CourseSectionData(
            usage_key=section.location,
            title=section.display_name,
            sequences=sequences_data
        )
        return section_data, hide_from_toc_set, visible_to_staff_only_set


    # Do the expensive modulestore access before starting a transaction...
    store = modulestore()
    sections = []
    hide_from_toc_set = set()
    visible_to_staff_only_set = set()
    with store.branch_setting(ModuleStoreEnum.Branch.published_only, course_key):
        course = store.get_course(course_key, depth=2)
        sections_data = []
        for section in course.get_children():
            section_data, sec_hide_from_toc, sec_visible_to_staff_only = _make_section_data(section)
            sections_data.append(section_data)
            hide_from_toc_set.update(sec_hide_from_toc)
            visible_to_staff_only_set.update(sec_visible_to_staff_only)

        sequences = OrderedDict()
        for section_data in sections_data:
            for seq_data in section_data.sequences:
                sequences[seq_data.usage_key] = seq_data

        course_outline_data = CourseOutlineData(
            course_key=course_key,
            title=course.display_name,
            published_at=course.subtree_edited_on,
            published_version=str(course.course_version),  # .course_version is a BSON obj
            sections=sections_data,
            sequences=sequences,
            visibility=CourseItemVisibilityData(
                hide_from_toc=frozenset(hide_from_toc_set),
                visible_to_staff_only=frozenset(visible_to_staff_only_set),
            )
        )

    replace_course_outline(course_outline_data)
