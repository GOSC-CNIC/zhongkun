from rest_framework import serializers


class OrganizationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    abbreviation = serializers.CharField()
    creation_time = serializers.DateTimeField()
    desc = serializers.CharField()
    longitude = serializers.FloatField(label='经度', default=0)
    latitude = serializers.FloatField(label='纬度', default=0)
    sort_weight = serializers.IntegerField()
