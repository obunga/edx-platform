import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

import attr
from django.contrib.auth import get_user_model
from django.db import transaction
from edx_django_utils.cache import TieredCache, get_cache_key
from opaque_keys.edx.keys import CourseKey, UsageKey

from .data import (
    CourseItemVisibilityData, CourseOutlineData, CourseSectionData,
    LearningSequenceData, UserCourseOutlineData, UserCourseOutlineDetailsData
)
from ..models import (
    CourseSection, CourseSectionSequence, LearningContext, LearningSequence
)
from .processors import ScheduleOutlineProcessor

User = get_user_model()
log = logging.getLogger(__name__)

# Public API...
__all__ = [
    'get_course_outline',
    'get_user_course_outline',
    'get_user_course_outline_details',
    'replace_course_outline',
]


def get_course_outline(course_key: CourseKey) -> CourseOutlineData:
    """
    Get the outline of a course run.

    There is no user-specific data or permissions applied in this function.
    """
    learning_context = _get_learning_context_for_outline(course_key)

    # Check to see if it's in the cache.
    cache_key = "learning_sequences.api.get_course_outline.v1.{}.{}".format(
        learning_context.context_key, learning_context.published_version
    )
    outline_cache_result = TieredCache.get_cached_response(cache_key)
    if outline_cache_result.is_found:
        return outline_cache_result.value

    # Fetch model
    section_models = CourseSection.objects \
                         .filter(learning_context=learning_context) \
                         .order_by('order')
    section_sequence_models = CourseSectionSequence.objects \
                                  .filter(learning_context=learning_context) \
                                  .order_by('order') \
                                  .select_related('sequence')

    # Build mapping of section.id keys to sequence lists. We pull the sections
    # separately to accurately represent empty sections/chapters.
    sec_ids_to_sequence_list = defaultdict(list)
    seq_keys_to_sequence = {}
    hide_from_toc_set = set()
    visible_to_staff_only_set = set()

    for sec_seq_model in section_sequence_models:
        sequence_model = sec_seq_model.sequence
        sequence_data = LearningSequenceData(
            usage_key=sequence_model.usage_key,
            title=sequence_model.title,
        )
        seq_keys_to_sequence[sequence_data.usage_key] = sequence_data
        sec_ids_to_sequence_list[sec_seq_model.section_id].append(sequence_data)
        if sec_seq_model.hide_from_toc:
            hide_from_toc_set.add(sequence_data.usage_key)
        if sec_seq_model.visible_to_staff_only:
            visible_to_staff_only_set.add(sequence_data.usage_key)

    sections_data = []
    for section_model in section_models:
        sections_data.append(
            CourseSectionData(
                usage_key=section_model.usage_key,
                title=section_model.title,
                sequences=sec_ids_to_sequence_list[section_model.id]
            )
        )
        if section_model.hide_from_toc:
            hide_from_toc_set.add(section_model.usage_key)
        if section_model.visible_to_staff_only:
            visible_to_staff_only_set.add(section_model.usage_key)

    outline_data = CourseOutlineData(
        course_key=learning_context.context_key,
        title=learning_context.title,
        published_at=learning_context.published_at,
        published_version=learning_context.published_version,
        sections=sections_data,
        sequences=seq_keys_to_sequence,
        visibility=CourseItemVisibilityData(
            hide_from_toc=frozenset(hide_from_toc_set),
            visible_to_staff_only=frozenset(visible_to_staff_only_set),
        )
    )
    TieredCache.set_all_tiers(cache_key, outline_data, 300)

    return outline_data


def _get_learning_context_for_outline(course_key: CourseKey) -> LearningContext:
    if course_key.deprecated:
        raise ValueError(
            "Learning Sequence API does not support Old Mongo courses: {}"
            .format(course_key),
        )
    try:
        learning_context = LearningContext.objects.get(context_key=course_key)
    except LearningContext.DoesNotExist:
        # Could happen if it hasn't been published.
        raise CourseOutlineData.DoesNotExist(
            "No CourseOutlineData for {}".format(course_key)
        )
    return learning_context


def get_user_course_outline(course_key: CourseKey,
                            user: User,
                            at_time: datetime):
    user_course_outline, _ = _get_user_course_outline_and_processors(course_key, user, at_time)
    return user_course_outline

def get_user_course_outline_details(course_key: CourseKey,
                                    user: User,
                                    at_time: datetime):
    user_course_outline, processors = _get_user_course_outline_and_processors(course_key, user, at_time)

    schedule_processor = processors['schedule']

    return UserCourseOutlineDetailsData(
        outline=user_course_outline,
        schedule=schedule_processor.schedule_data(user_course_outline)
    )

def _get_user_course_outline_and_processors(course_key: CourseKey,
                                            user: User,
                                            at_time: datetime): # how do you do tuple responses of ordereddicts again?
    """
    Get an outline customized for a particular user at a particular time.

    `user` is a Django User object (including the AnonymousUser)
    `at_time` should be a UTC datetime.datetime object.


    Have a method that returns UserCourseOutlineData and OutlineProcessors

    Have the public method only return UserCourseOutlineData

    Have a new type that combines UserCourseOutlineData with the output of some
    known subset of OutlineProcessors for things like schedule data.

    Use that last one in the view.

    """
    full_course_outline = get_course_outline(course_key)
    has_staff_access = False

    # These are processors that alter which sequences are visible to students.
    # For instance, certain sequences that are intentionally hidden or not yet
    # released. These do not need to be run for staff users.
    processor_classes = [
#        ('content_gating', ContentGatingOutlineProcessor),
#        ('milestones', MilestonesOutlineProcessor),
#        ('user_partitions', UserPartitionsOutlineProcessor),
        ('schedule', ScheduleOutlineProcessor),
    ]

    # Run each OutlineProcessor in order to figure out what items we have to
    # remove from the CourseOutline.
    processors = dict()
    usage_keys_to_remove = set()
    inaccessible_usage_keys = set()
    for name, processor_cls in processor_classes:
        # TODO: put some instrumentation here so we know what's taking longer...
        # Future optimization: This should be parallelizable (don't rely on a
        # particular ordering).
        processor = processor_cls(course_key, user, at_time)
        processors[name] = processor
        processor.load_data()
        if not has_staff_access:
            usage_keys_to_remove |= processor.usage_keys_to_remove(full_course_outline)
            inaccessible_usage_keys |= processor.inaccessible_usage_keys(full_course_outline)

    trimmed_course_outline = full_course_outline.remove(usage_keys_to_remove)
    accessible_sequences = set(trimmed_course_outline.sequences) - inaccessible_usage_keys

    user_course_outline = UserCourseOutlineData(
        base_outline=full_course_outline,
        user=user,
        at_time=at_time,
        accessible_sequences=accessible_sequences,
        **{
            name: getattr(trimmed_course_outline, name)
            for name in attr.fields_dict(CourseOutlineData)
        }
    )

    return user_course_outline, processors


def replace_course_outline(course_outline: CourseOutlineData):
    """
    Replace the model data stored for the Course Outline with the contents of
    course_outline (a CourseOutlineData).

    This isn't particularly optimized at the moment.
    """
    course_key = course_outline.course_key
    log.info("Generating CourseOutline for %s", course_key)
    log.info("CourseOutline: %s", course_outline)
    if course_key.deprecated:
        raise ValueError("CourseOutline generation not supported for Old Mongo courses")

    with transaction.atomic():
        # Update or create the basic LearningContext...
        learning_context = _update_learning_context(course_outline)

        # Wipe out the CourseSectionSequences join+ordering table so we can
        # delete CourseSection and LearningSequence objects more easily.
        learning_context.section_sequences.all().delete()

        _update_sections(course_outline, learning_context)
        _update_sequences(course_outline, learning_context)
        _update_course_section_sequences(course_outline, learning_context)


def _update_learning_context(course_outline: CourseOutlineData):
    learning_context, created = LearningContext.objects.update_or_create(
        context_key=course_outline.course_key,
        defaults={
            'title': course_outline.title,
            'published_at': course_outline.published_at,
            'published_version': course_outline.published_version
        }
    )
    if created:
        log.info("Created new LearningContext for %s", course_outline.course_key)
    else:
        log.info("Found LearningContext for %s, updating...", course_outline.course_key)

    return learning_context


def _update_sections(course_outline: CourseOutlineData, learning_context: LearningContext):
    # Add/update relevant sections...
    for order, section_data in enumerate(course_outline.sections):
        hide_from_toc = section_data.usage_key in course_outline.visibility.hide_from_toc
        visible_to_staff_only = section_data.usage_key in course_outline.visibility.visible_to_staff_only

        CourseSection.objects.update_or_create(
            learning_context=learning_context,
            usage_key=section_data.usage_key,
            defaults={
                'title': section_data.title,
                'order': order,
                'hide_from_toc': hide_from_toc,
                'visible_to_staff_only': visible_to_staff_only,
            }
        )
    # Delete sections that we don't want any more
    section_usage_keys_to_keep = [
        section_data.usage_key for section_data in course_outline.sections
    ]
    CourseSection.objects \
        .filter(learning_context=learning_context) \
        .exclude(usage_key__in=section_usage_keys_to_keep) \
        .delete()


def _update_sequences(course_outline: CourseOutlineData, learning_context: LearningContext):
    for section_data in course_outline.sections:
        for sequence_data in section_data.sequences:
            LearningSequence.objects.update_or_create(
                learning_context=learning_context,
                usage_key=sequence_data.usage_key,
                defaults={'title': sequence_data.title}
            )
    LearningSequence.objects \
        .filter(learning_context=learning_context) \
        .exclude(usage_key__in=course_outline.sequences) \
        .delete()


def _update_course_section_sequences(course_outline: CourseOutlineData, learning_context: LearningContext):
    section_models = {
        section_model.usage_key: section_model
        for section_model
        in CourseSection.objects.filter(learning_context=learning_context).all()
    }
    sequence_models = {
        sequence_model.usage_key: sequence_model
        for sequence_model
        in LearningSequence.objects.filter(learning_context=learning_context).all()
    }

    for order, section_data in enumerate(course_outline.sections):
        for sequence_data in section_data.sequences:
            hide_from_toc = sequence_data.usage_key in course_outline.visibility.hide_from_toc
            visible_to_staff_only = sequence_data.usage_key in course_outline.visibility.visible_to_staff_only
            CourseSectionSequence.objects.update_or_create(
                learning_context=learning_context,
                section=section_models[section_data.usage_key],
                sequence=sequence_models[sequence_data.usage_key],
                defaults={
                    'order': order,
                    'hide_from_toc': hide_from_toc,
                    'visible_to_staff_only': visible_to_staff_only,
                },
            )
