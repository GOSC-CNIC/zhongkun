from .model import Request, build_url


class CreateInstanceInput:
    PAY_TYPE_YEAR_MONTH = 'YEAR_MONTH'              # 包年包月
    PAY_TYPE_CHARGING_HOURS = 'CHARGING_HOURS'      # 按小时实时付费

    SYS_DISK_CODE_SSD = 'ebs.highIO.ssd'            # SSD硬盘
    SYS_DISK_CODE_HDD = 'ebs.hybrid.hdd'            # 高性能HDD硬盘

    IMAGE_CLASS_CODE_PUBLIC = 'ecs.image.public'    # 共有镜像
    IMAGE_CLASS_CODE_PRIVATE = 'ecs.image.private'  # 用户自定义镜像

    def __init__(
            self, region_id: str, azone_id: str,
            pay_type: str, period: int,
            vm_specification_code: str,
            sys_disk_specification_code: str, sys_disk_size: int,
            image_id: str, image_specification_class_code: str,
            instance_name: str, security_group_id: str,
            vpc_id: str, master_eni_subnet_id: str,
            base_quantity: int = 1,
            band_width_specification_code: str = None, band_width_size: str = None,
            password: str = None, host_name: str = None, description: str = None
    ):
        """
        :param region_id: 区域ID
        :param azone_id: 可用区ID
        :param pay_type: 计费方式,YEAR_MONTH（包年包月）；CHARGING_HOURS（按小时实时付费）
        :param period: 购买租期(月), 计费方式为YEAR_MONTH时需要
        :param vm_specification_code: 弹性云主机规格编码,
        :param sys_disk_specification_code: 系统盘规格编码, ebs.highIO.ssd（SSD硬盘）；ebs.hybrid.hdd（高性能HDD硬盘)
        :param sys_disk_size: 系统盘大小(G)
        :param image_id: 镜像ID
        :param image_specification_class_code: 镜像规格族, 共有镜像(ecs.image.public), 用户自定义镜像(ecs.image.private)
        :param instance_name: 实例名称(字母开头，包含字母数字，2到15个字符)
        :param base_quantity: 购买数量
        :param security_group_id: 绑定的安全组id
        :param vpc_id: 主网卡所在的VPC专有云ID
        :param master_eni_subnet_id: 主网卡所在的子网ID
        :param band_width_specification_code: EIP规格编码，如 eip.bgp.static
        :param band_width_size: EIP带宽1-500 Mbps,外网ip
        :param password: 云主机初始密码, root/Administrator
        :param host_name: 虚机hostname，不指定是使用instance_name
        :param description: 虚机描述
        """
        kwargs = {
            'regionId': region_id, 'azoneId': azone_id, 'payType': pay_type,
            'vmSpecificationCode': vm_specification_code,
            'sysDiskSpecificationCode': sys_disk_specification_code,
            'sysDiskSize': sys_disk_size, 'imageId': image_id,
            'imageSpecificationClassCode': image_specification_class_code,
            'instanceName': instance_name,
            'baseQuantity': base_quantity,
            'vpcId': vpc_id,
            'masterEniSubNetId': master_eni_subnet_id,
            'period': period
        }

        # if pay_type == 'YEAR_MONTH':
        #     kwargs['period'] = period

        if security_group_id:
            kwargs['securityGroupId'] = security_group_id

        if band_width_specification_code and band_width_size:
            kwargs['bandWidthSpecificationCode'] = band_width_specification_code
            kwargs['bandWidthSize'] = band_width_size

        if password:
            kwargs['password'] = password

        if host_name:
            kwargs['hostName'] = host_name

        if description:
            kwargs['description'] = description

        self.kwargs = kwargs

    @property
    def data(self):
        return self.kwargs


class Compute:
    Location = '/compute/ecs/instances'

    def __init__(self, endpoint_url: str, region_id: str, signer):
        self.endpoint_url = endpoint_url
        self.region_id = region_id
        self.signer = signer

    def _build_request(self, method: str, params: dict, data: dict = None):
        api = build_url(self.endpoint_url, self.Location)
        return Request(
            method=method,
            url=api,
            params=params,
            data=data
        )

    def create_server(self, input: CreateInstanceInput):
        params = {
            'Action': 'RunEcs'
        }
        request = self._build_request(method='POST', params=params, data=input.data)
        return request.do_request(self.signer)

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

    def list_private_images(self, page: int = None, size: int = 100, status: str = 'Available'):
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
