from rest_framework import serializers
from apps.app_netflow.models import MenuCategoryModel
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel


class ChartModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartModel
        fields = "__all__"
        # exclude = ('category',)


class MenuModelSerializer(serializers.ModelSerializer):
    # chart = ChartModelSerializer(read_only=True, many=True)

    class Meta:
        model = MenuModel
        # fields = "__all__"
        fields = ('id', 'name', 'sort_weight', 'remark', )


class MenuCategorySerializer(serializers.ModelSerializer):
    sub_categories = MenuModelSerializer(read_only=True, many=True)

    class Meta:
        model = MenuCategoryModel
        fields = ('id', 'name', 'sort_weight', 'remark', 'sub_categories',)
        # fields = '__all__'
