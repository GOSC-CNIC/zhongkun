# from rest_framework import serializers
#
#
# class OrganizationSerializer(serializers.Serializer):
#     id = serializers.CharField()
#     name = serializers.CharField()
#     name_en = serializers.CharField()
#     abbreviation = serializers.CharField()
#     creation_time = serializers.DateTimeField()
#     desc = serializers.CharField()
#     longitude = serializers.FloatField(label='经度', default=0)
#     latitude = serializers.FloatField(label='纬度', default=0)
#     sort_weight = serializers.IntegerField()
#
#
# class ContactSerializer(serializers.Serializer):
#     id = serializers.CharField()
#     name = serializers.CharField(label='姓名', max_length=128)
#     telephone = serializers.CharField(label='电话', max_length=11)
#     email = serializers.EmailField(label='邮箱地址')
#     address = serializers.CharField(label='联系地址', max_length=255)
#     creation_time = serializers.DateTimeField(label='创建时间')
#     update_time = serializers.DateTimeField(label='更新时间')
#     remarks = serializers.CharField(max_length=255, label='备注')
