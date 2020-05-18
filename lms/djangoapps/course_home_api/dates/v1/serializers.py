"""
Dates Tab Serializers. Represents the relevant dates for a Course.
"""


from rest_framework import serializers


class DateSummarySerializer(serializers.Serializer):
    """
    Serializer for Date Summary Objects.
    """
    contains_gated_content = serializers.BooleanField(default=False)
    date = serializers.DateTimeField()
    date_type = serializers.CharField()
    description = serializers.CharField()
    learner_has_access = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    title = serializers.CharField()

    def get_learner_has_access(self, block):
        learner_is_verified = self.context.get('learner_is_verified', False)
        return (not getattr(block, 'contains_gated_content', False)) or learner_is_verified

    def get_link(self, block):
        request = self.context.get('request')
        return request.build_absolute_uri(block.link)


class DatesTabSerializer(serializers.Serializer):
    course_date_blocks = DateSummarySerializer(many=True)
    course_number = serializers.CharField()
    display_reset_dates_text = serializers.BooleanField()
    learner_is_verified = serializers.BooleanField()
    user_language = serializers.CharField()
    user_timezone = serializers.CharField()
    verified_upgrade_link = serializers.URLField()
