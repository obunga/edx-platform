"""
Dates Tab Serializers. Represents the relevant dates for a Course.
"""


from rest_framework import serializers


class DateSummarySerializer(serializers.Serializer):
    """
    Serializer for Date Summary Objects.
    """
    date = serializers.DateTimeField()
    contains_gated_content = serializers.BooleanField(default=False)
    title = serializers.CharField()
    link = serializers.CharField()


class DatesTabSerializer(serializers.Serializer):
    course_date_blocks = DateSummarySerializer(many=True)
    course_number = serializers.CharField()
    learner_is_verified = serializers.BooleanField()
    user_language = serializers.CharField()
    user_timezone = serializers.CharField()
    verified_upgrade_link = serializers.URLField()
