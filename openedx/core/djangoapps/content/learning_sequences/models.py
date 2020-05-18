"""
Models for Learning Sequences and Course Outline generation.

Conventions:

1. Only things in the `api` package should ever import this file. Do NOT import
from views.py or anywhere else. Even if that means we have to give up some DRF
niceties.

2. The vast majority of what our public API promises should be efficiently
queryable with these models. We might occasionally reach into other systems
built for fast course-level queries (e.g. grading, scheduling), but we should
never touch ModuleStore or Block Transformers.

3. It's okay for some basic validation to happen at the model layer. Constraints
like uniqueness should absolutely be enforced at this layer. But business logic
should happen in the `api` package.

4. Try to avoid blob-like entites as much as possible and push things into
normalized tables. This may be unavoidable for things like arbitrary JSON
configuration though.

5. In general, keep models as a thin, dumb persistence layer. Let the `api`
package decide when and where it's safe to cache things.

6. Models and data.py datastructures don't have to map 1:1, but the convention
is that the data struct has a "...Data" appended to it. For instance,
LearningContext -> LearningContextData. This is because the Python name for
dataclasses (what attrs is close to), and for better backwards compatibility if
we want to adopt this convention elsewhere.

7. Strongly separate things that are intrinsic to Learning Sequences as a whole
vs. things that only apply to Sequences in the context of a Course. We have
other uses for sequences (e.g. Content Libraries, Pathways) and we want to keep
that separated.
"""
from django.db import models
from model_utils.models import TimeStampedModel

from opaque_keys.edx.django.models import CourseKeyField, LearningContextKeyField, UsageKeyField


class LearningContext(TimeStampedModel):
    """
    These are used to group Learning Sequences so that many of them can be
    pulled at once. We use this instead of a foreign key to CourseOverview
    because this table can contain things that are not courses.
    """
    id = models.BigAutoField(primary_key=True)
    context_key = LearningContextKeyField(
        max_length=255, db_index=True, unique=True, null=False
    )
    title = models.CharField(max_length=255)
    published_at = models.DateTimeField(null=False)
    published_version = models.CharField(max_length=255)

    class Meta:
        indexes = [
            models.Index(fields=['-published_at'])
        ]


class LearningSequence(TimeStampedModel):
    """
    The reason why this model doesn't have a direct foreign key to CourseSection
    is because we eventually want to have LearningSequences that exist outside
    of courses. Attributes that apply directly to all LearningSequences
    (usage_key, title, learning_context, etc.) will apply here, but anything
    that is specific to how a LearningContext is rendered for a course (e.g.
    permissions, staff visibility, is_entrance_exam) wil live in
    CourseSectionSequence.
    """
    id = models.BigAutoField(primary_key=True)
    learning_context = models.ForeignKey(
        LearningContext, on_delete=models.CASCADE, related_name='sequences'
    )
    usage_key = UsageKeyField(max_length=255)
    title = models.CharField(max_length=255)

    # Separate field for when this Sequence's content was last changed?
    class Meta:
        unique_together = (
            ('learning_context', 'usage_key'),
        )


class CourseContentVisibilityMixin(models.Model):
    """
    This stores XBlock information that affects outline level visibility for a
    single LearningSequence or Section in a course.

    We keep the XBlock field names here, even if they're somewhat misleading.
    Please read the comments carefully for each field.
    """
    # This is an obscure, OLX-only flag (there is no UI for it in Studio) that
    # lets you define a Sequence that is reachable by direct URL but not shown
    # in Course navigation. It was used for things like supplementary tutorials
    # that were not considered a part of the normal course path.
    hide_from_toc = models.BooleanField(null=False, default=False)

    # Restrict visibility to course staff, regardless of start date.
    visible_to_staff_only = models.BooleanField(null=False, default=False)

    class Meta:
        abstract = True


class CourseSection(CourseContentVisibilityMixin, TimeStampedModel):
    id = models.BigAutoField(primary_key=True)
    learning_context = models.ForeignKey(
        LearningContext, on_delete=models.CASCADE, related_name='sections'
    )
    usage_key = UsageKeyField(max_length=255)
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(null=False)

    class Meta:
        unique_together = (
            ('learning_context', 'usage_key'),
        )
        index_together = (
            ('learning_context', 'order'),
        )


class CourseSectionSequence(CourseContentVisibilityMixin, TimeStampedModel):
    """
    This is a join+ordering table, with entries that could get wiped out and
    recreated with every course publish. Do NOT make a ForeignKey against this
    table before implementing smarter replacement logic when publishing happens,
    or you'll see deletes all the time.

    CourseContentVisibilityMixin is applied here (and not in LearningSequence)
    because CourseContentVisibilityMixin describes attributes that are part of
    how a LearningSequence is used within a course, and may not apply to other
    kinds of LearningSequences.

    TODO: Shouldn't be deleting all the time, esp. since we have so much random
    course visibility data.
    """
    id = models.BigAutoField(primary_key=True)
    learning_context = models.ForeignKey(
        LearningContext, on_delete=models.CASCADE, related_name='section_sequences'
    )
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE)
    sequence = models.ForeignKey(LearningSequence, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(null=False)

    class Meta:
        index_together = (
            ('learning_context', 'order'),
        )
