"""
Dates Tab Serializers. Represents the relevant dates for a Course.
"""


from rest_framework import serializers


class DatesTabSerializer(serializers.Serializer):
    """
    Serializer for Date Summary Objects.
    """
    title = serializers.CharField()
    date = serializers.DateTimeField()
