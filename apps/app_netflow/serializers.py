from rest_framework import serializers
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel


class ChartModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartModel
        fields = "__all__"


class ChildDeptSerializer(serializers.ModelSerializer):
    sub_categories = serializers.SerializerMethodField()

    class Meta:
        model = MenuModel
        depth = 1

        fields = (
            'id',
            'name',
            # 'sort_weight',
            # 'remark',
            'sub_categories',
        )

    def get_sub_categories(self, obj):
        if obj.sub_categories:
            return ChildDeptSerializer(obj.sub_categories, many=True).data
        return None


class MenuModelSerializer(serializers.ModelSerializer):
    sub_categories = ChildDeptSerializer(many=True)

    class Meta:
        model = MenuModel
        fields = (
            'id',
            'name',
            # 'sort_weight',
            # 'remark',
            'sub_categories',
        )
        depth = 1


class CustomSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.meta = dict()
        super().__init__(*args, **kwargs)


class TimestampRangeSerializer(CustomSerializer):
    start = serializers.IntegerField(
        label="起始时间戳",
        help_text='起始时间戳',
        required=True,
        error_messages={'required': "起始时间戳start不能为空"}
    )
    end = serializers.IntegerField(
        label="结束时间戳",
        help_text='结束时间戳',
        required=True,
        error_messages={'required': "结束时间戳end不能为空"}
    )

    def validate_start(self, start):
        if not self.s_or_ns(start):
            raise serializers.ValidationError("start仅支持10位或19位.请检查: {}".format(start))
        self.meta["start"] = start
        return start

    def validate_end(self, end):
        if not self.s_or_ns(end):
            raise serializers.ValidationError("end仅支持10位或19位.请检查: {}".format(end))
        self.meta["end"] = end
        if self.meta.get("start") > end:
            raise serializers.ValidationError("start 应小于等于 end")
        return end

    @staticmethod
    def s_or_ns(ts):
        return len(str(ts)) in [10, 19]


class TrafficSerializer(TimestampRangeSerializer):
    chart = serializers.CharField(
        label="图表ID",
        help_text='图表ID',
        required=True,
        error_messages={'required': "图标ID不能为空"}
    )

    def validate_chart(self, chart):
        obj = ChartModel.objects.filter(id=chart)
        if not obj:
            raise serializers.ValidationError("ports参数无效")
        return chart
