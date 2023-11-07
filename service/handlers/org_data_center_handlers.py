from service.models import DataCenter, OrgDataCenter
from users.managers import get_user_by_name
from core import errors as exceptions


class OrgDataCenterHandler:

    def get_organization(self, id):
        dc = DataCenter.objects.filter(id=id)
        if not dc:
            raise exceptions.NotFound(message=f'数据中心不存在', status_code=404)
        return dc

    def get_users(self, user_list):
        # 获取管理员
        if not user_list:
            return None

        user_obj_list = []
        for user in user_list:
            try:
                u = get_user_by_name(username=user)
            except Exception as e:
                raise e
            user_obj_list.append(u)
        return user_obj_list

    def create_or_update_org_date_center(self, validated_data, user_list, org_id=None, flag=False):
        """
        创建或更新机构下的数据中心
        validated_data 基本信息
        user_list 管理员列表
        flag: true 创建  false 更新
        """

        user_obj_list = self.check_filed(validated_data, user_list)

        org_dc = None
        if flag:
            org_dc = OrgDataCenter()
        else:
            org_dc = OrgDataCenter.objects.filter(id=org_id).first()

        if org_dc is None:
            raise exceptions.NotFound(message=f'数据中心不存在', status_code=404)

        org_dc.name = validated_data.get('name')
        org_dc.name_en = validated_data.get('name_en')
        org_dc.organization_id = validated_data.get('organization')
        org_dc.longitude = float(validated_data.get('longitude'))
        org_dc.latitude = float(validated_data.get('latitude'))
        org_dc.sort_weight = int(validated_data.get('sort_weight'))
        org_dc.remark = validated_data.get('remark')
        org_dc.thanos_endpoint_url = validated_data.get('thanos_endpoint_url')
        org_dc.thanos_username = validated_data.get('thanos_username')
        org_dc.thanos_password = validated_data.get('thanos_password')
        org_dc.thanos_receive_url = validated_data.get('thanos_receive_url')
        org_dc.thanos_remark = validated_data.get('thanos_remark')
        org_dc.loki_endpoint_url = validated_data.get('loki_endpoint_url')
        org_dc.loki_username = validated_data.get('loki_username')
        org_dc.loki_password = validated_data.get('loki_password')
        org_dc.loki_receive_url = validated_data.get('loki_receive_url')
        org_dc.loki_remark = validated_data.get('loki_remark')

        try:
            if flag is True:
                org_dc.save(force_insert=True)
            else:
                org_dc.save(force_update=True)
        except Exception as e:
            raise e

        users = org_dc.users.all()
        for user in user_obj_list:
            if not users:
                org_dc.users.add(user)
                continue

            if not users.filter(username=user):
                org_dc.users.add(user)

        return org_dc

    def check_url_http(self, url):
        url_list = url.split("://")
        if url_list[0] not in ['https', 'http']:
            raise exceptions.ValidationError(message=f'参数{url}不正确', status_code=400)

    def check_filed(self, validated_data, user_list):

        organization_id = validated_data.get('organization')
        thanos_endpoint_url = validated_data.get('thanos_endpoint_url')
        thanos_receive_url = validated_data.get('thanos_receive_url')
        loki_endpoint_url = validated_data.get('loki_endpoint_url')
        loki_receive_url = validated_data.get('loki_receive_url')

        try:
            self.get_organization(id=organization_id)
            user_list = self.get_users(user_list=user_list)
        except Exception as e:
            raise e
        if thanos_endpoint_url:
            self.check_url_http(url=thanos_endpoint_url)

        if thanos_receive_url:
            self.check_url_http(url=thanos_receive_url)

        if loki_endpoint_url:
            self.check_url_http(url=loki_endpoint_url)

        if loki_receive_url:
            self.check_url_http(url=loki_receive_url)

        return user_list

    def create_org_dc(self, user_list, valid_data):
        return self.create_or_update_org_date_center(validated_data=valid_data, user_list=user_list, flag=True)

    def update_org_dc(self, user_list, valid_data, update_id):
        return self.create_or_update_org_date_center(validated_data=valid_data, user_list=user_list, org_id=update_id)
