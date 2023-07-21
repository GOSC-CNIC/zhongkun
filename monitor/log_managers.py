from core import errors
from api.serializers import log_serializers
from .models import LogSite


class LogSiteManager:
    @staticmethod
    def get_perm_log_site(user, log_type: str):
        queryset = LogSite.objects.select_related(
            'organization', 'site_type').order_by('sort_weight').all()

        if not user.is_federal_admin():
            queryset = queryset.filter(users__id=user.id)

        if log_type:
            queryset = queryset.filter(log_type=log_type)

        return queryset.distinct()

    def query(self, log_site: LogSite, limit: int):
        """
        :return:
            [
                {
                    "monitor":{
                        "name": "",
                        "name_en": "",
                        "job_tag": "",
                        "id": "",
                        "creation": "2020-11-02T07:47:39.776384Z"
                    },
                    "metric": {
                        "__name__": "ceph_cluster_total_used_bytes",
                        "instance": "10.0.200.100:9283",
                        "job": "Fed-ceph",
                        "receive_cluster": "obs",
                        "receive_replica": "0",
                        "tenant_id": "default-tenant"
                    },
                    "value": [
                        1630267851.781,
                        "0"                 # "0": 正常；”1“:警告
                    ]
                }
            ]
        :raises: Error
        """
        job_dict = log_serializers.LogSiteSerializer(log_site).data
        r = self.request_data(provider=log_site.provider, job=log_site.job_tag)
        if r:
            data = r[0]
            data['monitor'] = job_dict
        else:
            data = {'monitor': job_dict, 'value': None}

        return [data]

