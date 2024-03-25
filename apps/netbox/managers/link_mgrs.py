from datetime import date

from django.utils.translation import gettext as _
from django.db import transaction
from django.db.models import Q

from core import errors
from netbox.models import (
    OrgVirtualObject, ConnectorBox, Element, ElementLink, ElementDetailData, DistributionFrame, DistriFramePort,
    FiberCable, LeaseLine, OpticalFiber, Link
)


class ElementManager:
    @staticmethod
    def get_queryset():
        return Element.objects.all()

    @staticmethod
    def get_element_by_id(
            id: str,
    ) -> Element:
        element = ElementManager.get_queryset().filter(id=id).first()
        if element is None:
            raise errors.TargetNotExist(message=_('网元不存在'), code='ElementNotExist')
        return element

    @staticmethod
    def get_element_by_object(
            object_type: str,
            object_id: str,
    ) -> Element:
        element = ElementManager.get_queryset().filter(object_id=object_id, object_type=object_type).first()
        if element is None:
            raise errors.TargetNotExist(message=_('网元不存在'), code='ElementNotExist')
        return element

    @staticmethod
    def create_element(
            object_id: str,
            object_type: Element.Type
    ) -> Element:
        element = Element(
            object_id=object_id,
            object_type=object_type,
        )
        element.save(force_insert=True)
        return element

    @staticmethod
    def get_element_detail_data_by_id(
        id: str,
    ) -> ElementDetailData:
        element = ElementManager.get_element_by_id(id=id)
        object_type = element.object_type
        if object_type == Element.Type.LEASE_LINE:
            lease = LeaseLineManager.get_leaseline(id=element.object_id)
            return ElementDetailData(_type=object_type, lease=lease)
        elif object_type == Element.Type.OPTICAL_FIBER:
            fiber = OpticalFiberManager.get_opticalfiber(id=element.object_id)
            return ElementDetailData(_type=object_type, fiber=fiber)
        elif object_type == Element.Type.DISTRIFRAME_PORT:
            port = DistriFramePortManager.get_distriframeport(id=element.object_id)
            return ElementDetailData(_type=object_type, port=port)
        elif object_type == Element.Type.CONNECTOR_BOX:
            box = ConnectorBoxManager.get_connectorbox(id=element.object_id)
            return ElementDetailData(_type=object_type, box=box)
        else:
            raise errors.Error(message=_(f'无法识别的网元种类, type: {object_type}'))


class ConnectorBoxManager:
    @staticmethod
    def get_queryset():
        return ConnectorBox.objects.all()

    @staticmethod
    def get_connectorbox(id: str):
        """
        :raises: ConnectorBoxNotExist
        """
        connectorbox = ConnectorBoxManager.get_queryset().filter(id=id).first()
        if connectorbox is None:
            raise errors.TargetNotExist(message=_('光缆熔纤包不存在'), code='ConnectorBoxNotExist')
        return connectorbox

    @staticmethod
    def create_connectorbox(
            number: str,
            place: str,
            remarks: str,
            location: str,
    ) -> ConnectorBox:
        with transaction.atomic():
            connectorbox_id = ConnectorBox().generate_id()
            element = ElementManager.create_element(object_id=connectorbox_id, object_type=Element.Type.CONNECTOR_BOX)
            connectorbox = ConnectorBox(
                id=connectorbox_id,
                number=number,
                place=place,
                remarks=remarks,
                location=location,
                element=element
            )
            connectorbox.save(force_insert=True)
        return connectorbox

    @staticmethod
    def filter_queryset(is_linked: bool = None):
        qs = ConnectorBoxManager.get_queryset()
        if is_linked is not None:
            linked_object_id_list = ElementLink.get_linked_object_id_list(object_type=Element.Type.CONNECTOR_BOX)
            if is_linked is True:
                qs = qs.filter(id__in=linked_object_id_list)
            else:
                qs = qs.exclude(id__in=linked_object_id_list)
        return qs


class DistriFramePortManager:
    @staticmethod
    def get_queryset():
        return DistriFramePort.objects.all()

    @staticmethod
    def get_distriframeport(id: str):
        """
        :raises: DistriFramePortNotExist
        """
        distriframeport = DistriFramePortManager.get_queryset().filter(id=id).first()
        if distriframeport is None:
            raise errors.TargetNotExist(message=_('配线架端口不存在'), code='DistriFramePortNotExist')
        return distriframeport

    @staticmethod
    def _generate_default_distriframe_port_number(
            row: int,
            col: int,
            distriframe: DistributionFrame
    ) -> str:
        return "{distriframe_number}({row},{col})".format(
            distriframe_number=distriframe.number, row=row, col=col)

    @staticmethod
    def create_distriframe_port(
            row: int,
            col: int,
            distriframe: DistributionFrame
    ) -> DistriFramePort:
        distriframe_port_id = DistriFramePort().generate_id()
        element = ElementManager.create_element(object_id=distriframe_port_id,
                                                object_type=Element.Type.DISTRIFRAME_PORT)
        distriframe_port = DistriFramePort(
            id=distriframe_port_id,
            number=DistriFramePortManager._generate_default_distriframe_port_number(
                distriframe=distriframe, row=row, col=col),
            row=row,
            col=col,
            distribution_frame=distriframe,
            element=element
        )
        distriframe_port.save(force_insert=True)
        return distriframe_port

    @staticmethod
    def filter_queryset(is_linked: bool = None, distribution_frame_id: str = None):
        qs = DistriFramePortManager.get_queryset()
        if distribution_frame_id is not None:
            qs = qs.filter(distribution_frame_id=distribution_frame_id)
        if is_linked is not None:
            linked_object_id_list = ElementLink.get_linked_object_id_list(object_type=Element.Type.DISTRIFRAME_PORT)
            if is_linked is True:
                qs = qs.filter(id__in=linked_object_id_list)
            else:
                qs = qs.exclude(id__in=linked_object_id_list)
        return qs


class DistriFrameManager:
    @staticmethod
    def get_queryset():
        return DistributionFrame.objects.all()

    @staticmethod
    def get_distriframe(id: str):
        """
        :raises: DistributionFrameNotExist
        """
        distriframe = DistriFrameManager.get_queryset().filter(id=id).first()
        if distriframe is None:
            raise errors.TargetNotExist(message=_('配线架不存在'), code='DistributionFrameNotExist')
        return distriframe

    @staticmethod
    def create_distriframe(
            number: str,
            model_type: str,
            row_count: int,
            col_count: int,
            place: str,
            link_org: OrgVirtualObject,
            remarks: str
    ) -> DistributionFrame:
        with transaction.atomic():
            # 创建光缆记录
            distriframe = DistributionFrame(
                number=number,
                model_type=model_type,
                row_count=row_count,
                col_count=col_count,
                place=place,
                remarks=remarks,
                link_org=link_org
            )
            distriframe.save(force_insert=True)
            # 创建光纤记录
            for i in range(1, row_count + 1):
                for j in range(1, col_count + 1):
                    DistriFramePortManager.create_distriframe_port(row=i, col=j, distriframe=distriframe)

        return distriframe


class FiberCableManager:
    @staticmethod
    def get_queryset():
        return FiberCable.objects.all()

    @staticmethod
    def get_fibercable(id: str):
        """
        :raises: FiberCableNotExist
        """
        fibercable = FiberCableManager.get_queryset().filter(id=id).first()
        if fibercable is None:
            raise errors.TargetNotExist(message=_('光缆不存在'), code='FiberCableNotExist')
        return fibercable

    @staticmethod
    def create_fibercable(
            number: str,
            fiber_count: int,
            length: float,
            endpoint_1: str,
            endpoint_2: str,
            remarks: str
    ) -> FiberCable:
        with transaction.atomic():
            # 创建光缆记录
            fibercable = FiberCable(
                number=number,
                fiber_count=fiber_count,
                length=length,
                endpoint_1=endpoint_1,
                endpoint_2=endpoint_2,
                remarks=remarks
            )
            fibercable.save(force_insert=True)
            # 创建光纤记录
            for i in range(1, fiber_count + 1):
                OpticalFiberManager.create_opticalfiber(sequence=i, fibercable=fibercable)

        return fibercable

    @staticmethod
    def filter_queryset(search: str = None):
        qs = FiberCableManager.get_queryset()
        if qs is not None and search is not None:
            q = Q(number__icontains=search) | Q(endpoint_1__icontains=search) \
                | Q(endpoint_2__icontains=search) | Q(remarks__icontains=search)
            qs = qs.filter(q)
        return qs

    @staticmethod
    def get_opticalfiber_queryset(fibercable: FiberCable):
        if fibercable is not None:
            return fibercable.fibercable_opticalfiber.all()


class LeaseLineManager:
    @staticmethod
    def get_queryset():
        return LeaseLine.objects.all()

    @staticmethod
    def get_leaseline(id: str):
        """
        :raises: LeaseLineNotExist
        """
        leaseline = LeaseLineManager.get_queryset().filter(id=id).first()
        if leaseline is None:
            raise errors.TargetNotExist(message=_('租用线路不存在'), code='LeaseLineNotExist')
        return leaseline

    @staticmethod
    def create_leaseline(
            private_line_number: str,
            lease_line_code: str,
            line_username: str,
            endpoint_a: str,
            endpoint_z: str,
            line_type: str,
            cable_type: str,
            bandwidth: float,
            length: int,
            provider: str,
            enable_date: date,
            is_whithdrawal: bool,
            money: float,
            remarks: str
    ) -> LeaseLine:
        with transaction.atomic():
            leaseline_id = LeaseLine().generate_id()
            # 创建网元记录
            element = ElementManager.create_element(object_id=leaseline_id, object_type=Element.Type.LEASE_LINE)
            # 创建租用线路
            leaseline = LeaseLine(
                id=leaseline_id,
                private_line_number=private_line_number,
                lease_line_code=lease_line_code,
                line_username=line_username,
                endpoint_a=endpoint_a,
                endpoint_z=endpoint_z,
                line_type=line_type,
                cable_type=cable_type,
                bandwidth=bandwidth,
                length=length,
                provider=provider,
                enable_date=enable_date,
                is_whithdrawal=is_whithdrawal,
                money=money,
                remarks=remarks,
                element=element
            )
            leaseline.save(force_insert=True)
        return leaseline

    @staticmethod
    def update_leaseline(
            leaseline: LeaseLine,
            private_line_number: str,
            lease_line_code: str,
            line_username: str,
            endpoint_a: str,
            endpoint_z: str,
            line_type: str,
            cable_type: str,
            bandwidth: float,
            length: int,
            provider: str,
            enable_date: date,
            is_whithdrawal: bool,
            money: float,
            remarks: str
    ) -> LeaseLine:
        leaseline.private_line_number = private_line_number
        leaseline.lease_line_code = lease_line_code
        leaseline.line_username = line_username
        leaseline.endpoint_a = endpoint_a
        leaseline.endpoint_z = endpoint_z
        leaseline.line_type = line_type
        leaseline.cable_type = cable_type
        leaseline.bandwidth = bandwidth
        leaseline.length = length
        leaseline.provider = provider
        leaseline.enable_date = enable_date
        leaseline.is_whithdrawal = is_whithdrawal
        leaseline.money = money
        leaseline.remarks = remarks
        leaseline.save(force_update=True)
        return leaseline

    @staticmethod
    def filter_queryset(
        is_linked: bool = None, is_whithdrawal: bool = None,  search: str = None,
        enable_date_start: date = None, enable_date_end: date = None):
        qs = LeaseLineManager.get_queryset()
        if is_linked is not None:
            linked_object_id_list = ElementLink.get_linked_object_id_list(object_type=Element.Type.LEASE_LINE)
            if is_linked is True:
                qs = qs.filter(id__in=linked_object_id_list)
            else:
                qs = qs.exclude(id__in=linked_object_id_list)
        lookups = {}
        if is_whithdrawal is not None:
            lookups['is_whithdrawal'] = is_whithdrawal

        if enable_date_start:
            lookups['enable_date__gte'] = enable_date_start

        if enable_date_end:
            lookups['enable_date__lte'] = enable_date_end
        qs = qs.filter(**lookups)
        if search:
            q = Q(private_line_number__icontains=search) | Q(lease_line_code__icontains=search) \
                | Q(line_username__icontains=search) | Q(endpoint_a__icontains=search) \
                | Q(endpoint_z__icontains=search) | Q(remarks__icontains=search)

            qs = qs.filter(q)

        return qs


class LinkManager:
    @staticmethod
    def get_queryset():
        return Link.objects.all()

    @staticmethod
    def get_link(link_id: str):
        """
        :raises: LinkNotExist
        """
        link = LinkManager.get_queryset().filter(id=link_id).first()
        if link is None:
            raise errors.TargetNotExist(message=_('链路不存在'), code='LinkNotExist')

        return link

    @staticmethod
    def create_elementlink(
            element: Element,
            link: Link,
            index: int,
            sub_index: int = 0,
    ) -> ElementLink:
        elementlink = ElementLink(
            element=element,
            link=link,
            index=index,
            sub_index=sub_index
        )
        elementlink.save(force_insert=True)
        return elementlink

    @staticmethod
    def create_link(
            number: str,
            user: str,
            endpoint_a: str,
            endpoint_z: str,
            bandwidth: float,
            description: str,
            line_type: str,
            business_person: str,
            build_person: str,
            link_status: str,
            remarks: str,
            enable_date: date,
            link_element: list,
    ) -> Link:
        with transaction.atomic():
            link = Link(
                number=number,
                user=user,
                endpoint_a=endpoint_a,
                endpoint_z=endpoint_z,
                bandwidth=bandwidth,
                description=description,
                line_type=line_type,
                business_person=business_person,
                build_person=build_person,
                link_status=link_status,
                remarks=remarks,
                enable_date=enable_date,
            )
            link.save(force_insert=True)
            for t in link_element:
                element = ElementManager.get_element_by_id(t['element_id'])
                LinkManager.create_elementlink(
                    element=element, link=link,
                    index=t['index'], sub_index=t['sub_index'])
        return link

    @staticmethod
    def is_valid_link_element(link_element: list):
        """link_element的数据库校验"""
        elements = [ElementManager.get_element_by_id(t['element_id']) for t in link_element]
        # 链路位置相同的网元类型必须相同
        object_type = ''
        for i in range(len(link_element)):
            if i > 0 and link_element[i - 1]['index'] == link_element[i]['index']:
                if elements[i].object_type != object_type:
                    raise errors.InvalidArgument(message=_('存在链路位置相同的不同类型的网元'))
            object_type = elements[i].object_type
        for element in elements:
            if not element.is_linkable():
                raise errors.InvalidArgument(message=_(f'不能在网元{element}上创建新链路'))

    @staticmethod
    def filter_queryset(link_status: list = None):
        qs = LinkManager.get_queryset()

        if link_status is not None:
            qs = qs.filter(link_status__in=link_status)

        return qs


class OpticalFiberManager:
    @staticmethod
    def get_queryset():
        return OpticalFiber.objects.all()

    @staticmethod
    def get_opticalfiber(id: str):
        """
        :raises: OpticalFiberNotExist
        """
        opticalfiber = OpticalFiberManager.get_queryset().filter(id=id).first()
        if opticalfiber is None:
            raise errors.TargetNotExist(message=_('光纤不存在'), code='OpticalFiberNotExist')
        return opticalfiber

    @staticmethod
    def create_opticalfiber(
        sequence: int,
        fibercable: FiberCable
    ) -> OpticalFiber:
        opticalfiber_id = OpticalFiber().generate_id()
        with transaction.atomic():
            element = ElementManager.create_element(object_id=opticalfiber_id, object_type=Element.Type.OPTICAL_FIBER)
            opticalfiber = OpticalFiber(
                id=opticalfiber_id,
                fiber_cable=fibercable,
                sequence=sequence,
                element=element
            )
            opticalfiber.save(force_insert=True)

        return opticalfiber

    @staticmethod
    def filter_queryset(is_linked: bool = None, fiber_cable_id: str = None):
        qs = OpticalFiberManager.get_queryset()
        if fiber_cable_id is not None:
            # tips:need verify fibercable existed?
            # fibercable = FiberCableManager.get_fibercable(fiber_cable_id)
            qs = qs.filter(fiber_cable_id=fiber_cable_id)
        if is_linked is not None:
            linked_object_id_list = ElementLink.get_linked_object_id_list(object_type=Element.Type.OPTICAL_FIBER)
            if is_linked is True:
                qs = qs.filter(id__in=linked_object_id_list)
            else:
                qs = qs.exclude(id__in=linked_object_id_list)

        return qs
