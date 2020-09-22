from .. import inputs
from . import exceptions


class InputValidator:
    @staticmethod
    def create_server_validate(params: inputs.ServerCreateInput):
        remarks = params.remarks if params.remarks else 'GOSC'
        try:
            center_id = int(params.region_id)
            image_id = int(params.image_id)
            vlan_id = int(params.network_id) if params.network_id else 0
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
        elif params.flavor_id:
            try:
                flavor_id = int(params.flavor_id)
            except ValueError as e:
                raise exceptions.APIInvalidParam(extend_msg=str(e))
            data['flavor_id'] = flavor_id
        else:
            raise exceptions.APIInvalidParam(extend_msg='no found param "flavor_id" or "ram","vcpu"')

        return data

