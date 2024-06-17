from .. import inputs
from . import exceptions


class InputValidator:
    @staticmethod
    def create_server_validate(params: inputs.ServerCreateInput):
        remarks = params.remarks if params.remarks else 'zhongkun'
        if len(remarks) > 200:
            remarks = remarks[0:200]

        try:
            center_id = int(params.region_id)
            image_id = int(params.image_id)
            vlan_id = int(params.network_id) if params.network_id else 0
            group_id = None
            if params.azone_id:
                group_id = int(params.azone_id)
        except ValueError as e:
            raise exceptions.APIInvalidParam(extend_msg=str(e))

        if image_id <= 0:
            raise exceptions.APIInvalidParam('invalid param "image_id"')

        data = {
            'center_id': center_id,
            'image_id': image_id,
            'remarks': remarks
        }
        if vlan_id > 0:
            data['vlan_id'] = vlan_id

        if params.ram and params.vcpu:
            try:
                ram = int(params.ram)
                vcpu = int(params.vcpu)
            except ValueError as e:
                raise exceptions.APIInvalidParam(extend_msg=str(e))

            data['mem'] = ram
            data['vcpu'] = vcpu
        else:
            raise exceptions.APIInvalidParam(extend_msg='no found param "ram" and "vcpu"')

        if params.systemdisk_size is not None:
            try:
                data['sys_disk_size'] = int(params.systemdisk_size)
            except ValueError as e:
                raise exceptions.APIInvalidParam(extend_msg=str(e))

        if group_id:
            data['group_id'] = group_id

        return data

    @staticmethod
    def create_disk_validate(params: inputs.DiskCreateInput):
        remarks = params.description if params.description else '一体云'
        try:
            center_id = int(params.region_id)
            size_gib = int(params.size_gib)
            group_id = None
            if params.azone_id:
                group_id = int(params.azone_id)
        except ValueError as e:
            raise exceptions.APIInvalidParam(extend_msg=str(e))

        data = {
            'center_id': center_id,
            'size': size_gib,
            'remarks': remarks
        }

        if group_id:
            data['group_id'] = group_id

        return data
