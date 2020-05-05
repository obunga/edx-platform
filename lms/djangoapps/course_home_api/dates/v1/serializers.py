"""
Dates Tab Serializers. Represents the relevant dates for a Course.
"""


from rest_framework import serializers


class DateSummarySerializer(serializers.Serializer):
    """
    Serializer for Date Summary Objects.
    """
    title = serializers.CharField()
    date = serializers.DateTimeField()


class DatesTabSerializer(serializers.Serializer):
    course_number = serializers.CharField()
    course_date_blocks = DateSummarySerializer(many=True)
    verified_upgrade_link = serializers.URLField()
    learner_is_verified = serializers.BooleanField()
    user_timezone = serializers.CharField()
    user_language = serializers.CharField()
