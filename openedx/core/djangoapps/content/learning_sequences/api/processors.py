"""
Expectation for all OutlineProcessors are:

* something to do a one-time load of data for an entire course
* a method to call to emit a list of usage_keys to hide
* a method to call to add any data that is relevant to this system.

# Processors that we need:

Attributes that apply to both Sections and Sequences
* start
* .hide_from_toc

Might make sense to put this whole thing as a "privte" module in an api package,
with the understanding that it's not part of the external contract yet.


"""
from collections import defaultdict

from edx_when.api import get_dates_for_course

from .data import ScheduleData, ScheduleItemData

class ScheduleOutlineProcessor:

    def load_data_for_course(self, course_key, user):
        # (usage_key, 'due'): datetime.datetime(2019, 12, 11, 15, 0, tzinfo=<UTC>)
        self.dates = get_dates_for_course(course_key, user)

    def sequence_keys_to_hide(self, full_course_outline):
        """
        Each
        """
        # Return a set/frozenset of usage keys to hide
        pass

    def data_to_add(self, updated_course_outline):
        """
        Return the data we want to add to this CourseOutlineData.

        Unlike `sequence_keys_to_hide`, this method gets a CourseOutlineData
        that only has those LearningSequences that

        This should have assignment types as well?
        """
        keys_to_schedule_fields = defaultdict(dict)
        for (usage_key, field_name), date in self.dates.items():
            if usage_key in updated_course_outline.sequences:
                keys_to_schedule_fields[usage_key][field_name] = date
        return ScheduleData(sequences={
            usage_key: ScheduleItemData(
                usage_key=usage_key,
                start=fields.get('start'),
                due=fields.get('due'),
            )
            for usage_key, fields in keys_to_schedule_fields.items()
        })

    #def disable_set(self, course_outline):
    #    # ???
    #   pass


class CourseVisiblityProcessor:
    pass



def process():
    # These are processors that alter which sequences are visible to students.
    # For instance, certain sequences that are intentionally hidden or not yet
    # released. These do not need to be run for staff users.
    visibility_processors = [

        ScheduleOutlineProcessor(),
    ]

    # Phase 1:
    sequence_keys_to_hide = set()
    for processor in processors:
        sequence_keys_to_hide.update(processor.sequence_keys_to_hide())

    # What is the desired behavior if you have a Chapter with no sequences?
    # I guess we keep it?
    outline_with_hidden_stuff = hide_sequences

    for processor in processors:
        pass