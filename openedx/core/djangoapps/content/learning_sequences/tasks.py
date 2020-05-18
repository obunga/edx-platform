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
    CourseOutlineData, CourseSectionData, LearningSequenceData, VisibilityData
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
        sequences_data = []
        for sequence in section.get_children():
            sequences_data.append(
                LearningSequenceData(
                    usage_key=sequence.location,
                    title=sequence.display_name,
                    visibility=VisibilityData(
                        hide_from_toc=sequence.hide_from_toc,
                        visible_to_staff_only=sequence.visible_to_staff_only
                    ),
                )
            )

        section_data = CourseSectionData(
            usage_key=section.location,
            title=section.display_name,
            sequences=sequences_data,
            visibility=VisibilityData(
                hide_from_toc=section.hide_from_toc,
                visible_to_staff_only=section.visible_to_staff_only
            ),
        )
        return section_data


    # Do the expensive modulestore access before starting a transaction...
    store = modulestore()
    sections = []
    with store.branch_setting(ModuleStoreEnum.Branch.published_only, course_key):
        course = store.get_course(course_key, depth=2)
        sections_data = []
        for section in course.get_children():
            section_data = _make_section_data(section)
            sections_data.append(section_data)

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
        )

    replace_course_outline(course_outline_data)
