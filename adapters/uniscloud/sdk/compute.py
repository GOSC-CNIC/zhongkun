from .model import Request, build_url


class Compute:
    Location = '/compute/ecs/instances'

    def __init__(self, endpoint_url: str, region_id: str, signer):
        self.endpoint_url = endpoint_url
        self.region_id = region_id
        self.signer = signer

    def _build_request(self, method: str, params):
        api = build_url(self.endpoint_url, self.Location)
        return Request(
            method=method,
            url=api,
            params=params
        )

    def create_server(self):
        request = Request(
            method=''
        )

    def rebuild_server(self, instance_id: str, image_id: str, password: str):
        params = {
            'Action': 'RebuildEcs',
            'RegionId': self.region_id,
            'InstanceId': instance_id,
            'ImageId': image_id,
            'Password': password
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)

    def list_servers(self, page: int = None, size: int = None):
        params = {
            'Action': 'DescribeEcs',
            'RegionId': self.region_id
        }
        if page:
            params['Page'] = page

        if size:
            params['Size'] = size

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)

    def action_server(self, instance_id: str, action: str):
        params = {
            'Action': action,
            'RegionId': self.region_id,
            'InstanceId': instance_id
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)

    def detail_server(self, instance_id: str):
        return self.action_server(instance_id, action='DetailEcs')

    def start_server(self, instance_id: str):
        return self.action_server(instance_id, action='StartEcs')

    def stop_server(self, instance_id: str):
        return self.action_server(instance_id, action='StopEcs')

    def reboot_server(self, instance_id: str):
        return self.action_server(instance_id, action='RebootEcs')

    def delete_server(self, instance_id: str):
        return self.action_server(instance_id, action='DeleteEcs')

    def get_server_vnc(self, instance_id: str):
        return self.action_server(instance_id, action='GetEcsVnc')

    def get_server_password(self, instance_id: str):
        return self.action_server(instance_id, action='GetEcsPassword')

    def reset_server_password(self, instance_id: str, password: str):
        params = {
            'Action': 'ResetEcsPassword',
            'RegionId': self.region_id,
            'InstanceId': instance_id,
            'Password': password
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)

    def list_images(self, page: int = None, size: int = 100, status: str = 'Available'):
        """

        :param status: 镜像状态筛选, []
        """
        params = {
            'Action': 'DescribeImages',
            'RegionId': self.region_id,
            'Status': status,
            'Size': size
        }
        if page:
            params['Page'] = page

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)
