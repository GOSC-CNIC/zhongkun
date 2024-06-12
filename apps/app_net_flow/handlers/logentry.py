import json
import datetime
from apps.app_net_flow.models import NetflowLogEntryModel
from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import DELETION
from django.forms.models import model_to_dict
from django.contrib.admin.options import get_content_type_for_model


class NetflowLogEntry:
    @staticmethod
    def model_to_dict(obj):
        item = model_to_dict(obj)
        item["id"] = obj.id
        temp = dict()
        for k, v in item.items():
            if isinstance(v, datetime.date):
                temp[k] = str(v)
        item.update(temp)
        return item

    def log_addition(self, request, obj, ):
        message = [{"added": {}}, {}, self.model_to_dict(obj)]
        return NetflowLogEntryModel.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=ADDITION,
            change_message=json.dumps(message, ensure_ascii=False),
        )

    def log_change(self, request, old, new):
        old_dict = self.model_to_dict(old)
        new_dict = self.model_to_dict(new)
        key_list = list()
        for k, v in old_dict.items():
            if new_dict[k] != v:
                key_list.append(k)

        message = [{"changed": {"fields": key_list}}, old_dict, new_dict]
        return NetflowLogEntryModel.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(new).pk,
            object_id=new.pk,
            object_repr=str(new),
            action_flag=CHANGE,
            change_message=json.dumps(message, ensure_ascii=False),
        )

    def log_deletion(self, request, obj):
        message = [{"deleted": {}}, self.model_to_dict(obj), {}]
        return NetflowLogEntryModel.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=DELETION,
            change_message=json.dumps(message, ensure_ascii=False),
        )
