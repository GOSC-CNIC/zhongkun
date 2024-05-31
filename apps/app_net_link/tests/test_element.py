from datetime import date

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.app_net_link.models import OpticalFiber, ConnectorBox, DistriFramePort, LeaseLine, Element
from apps.app_net_link.managers.link import FiberCableManager, DistriFrameManager, ConnectorBoxManager, LeaseLineManager
from apps.app_net_link.managers.common import NetLinkUserRoleWrapper
from apps.app_net_link.permissions import LinkIPRestrictor


class TaskTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')

        u2_roler = NetLinkUserRoleWrapper(self.user2)
        u2_roler.user_role = u2_roler.get_or_create_user_role()
        u2_roler.set_link_readonly(True)

        u3_roler = NetLinkUserRoleWrapper(self.user3)
        u3_roler.user_role = u3_roler.get_or_create_user_role()
        u3_roler.set_link_admin(True)

        LinkIPRestrictor.add_ip_rule(ip_value='0.0.0.0/0')
        LinkIPRestrictor.clear_cache()

        self.cable = FiberCableManager.create_fibercable(
            number='SM-test',
            fiber_count=30,
            length=30.5,
            endpoint_1='软件园',
            endpoint_2='古脊椎',
            remarks='test-remark'
        )
        self.distriframe = DistriFrameManager.create_distriframe(
            number='test_distriframe_number1',
            model_type='sc',
            row_count=6,
            col_count=12,
            place='位于铁科大厦一层弱电间，普天72芯一体化机框',
            remarks='【51893383随机呼转张效军18618417973和张东升13910987916】51893383找罗工、唐工',
            link_org=None
        )
        self.connectorbox = ConnectorBoxManager.create_connectorbox(
            number='test_connector2',
            place='test_place2',
            remarks='',
            location='',
        )
        self.leaseline = LeaseLineManager.create_leaseline(
            private_line_number='00645713',
            lease_line_code='天津空港物流加工区西七道32号',
            line_username='天津工业生物技术研究所',
            endpoint_a='北京市海淀区中关村南四街4号',
            endpoint_z='天津空港物流加工区西七道32号',
            line_type='接入网',
            cable_type='MSTP电路',
            bandwidth=400,
            length=None,
            provider='联通（北京）',
            enable_date=date.fromisoformat('2021-10-05'),
            is_whithdrawal=False,
            money=300.20,
            remarks='电路代号：北京天津ANE0365NP，起租时间2010.08.16,2014-1-1日由30M扩容为100M，2017年7月28日由100M扩容至150M,2019年8月由150M升级为250M.20201017升级到400M。'
        )

    def test_retrieve_element(self):
        # user role 
        fiber_element_id = OpticalFiber.objects.first().element.id
        port_element_id = DistriFramePort.objects.first().element.id
        box_element_id = ConnectorBox.objects.first().element.id
        lease_element_id = LeaseLine.objects.first().element.id
        base_url = reverse('net_link-api:link-element-detail',kwargs={'id': fiber_element_id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.user3)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)

        # Invalid id
        base_url = reverse('net_link-api:link-element-detail',kwargs={'id': '  '})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # element not exist
        base_url = reverse('net_link-api:link-element-detail', kwargs={'id': '123'})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='ElementNotExist', response=response)

        # fiber
        base_url = reverse('net_link-api:link-element-detail',kwargs={'id': fiber_element_id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'type', 'fiber', 'lease', 'port', 'box'
        ], response.data)
        self.assertEqual(response.data['type'], Element.Type.OPTICAL_FIBER)
        self.assertKeysIn([
            'id', 'sequence', 'fiber_cable', 'is_linked', 'element_id', 'link_id'
        ], response.data['fiber'])
        self.assertKeysIn([
            'id', 'number'
        ], response.data['fiber']['fiber_cable'])
        self.assertEqual(fiber_element_id, response.data['fiber']['element_id'])
        self.assertEqual(None, response.data['lease'])
        self.assertEqual(None, response.data['port'])
        self.assertEqual(None, response.data['box'])

        # lease
        base_url = reverse('net_link-api:link-element-detail',kwargs={'id': lease_element_id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['type'], Element.Type.LEASE_LINE)
        self.assertKeysIn([
            'id', 'private_line_number', 'lease_line_code', 'line_username', 'endpoint_a', 'endpoint_z',
            'line_type', 'cable_type', 'bandwidth', 'length', 'provider', 'enable_date', 'is_whithdrawal',
            'money', 'remarks', 'is_linked', 'element_id', 'link_id'
        ], response.data['lease'])
        self.assertEqual(lease_element_id,
                         response.data['lease']['element_id'])
        self.assertEqual(None, response.data['fiber'])
        self.assertEqual(None, response.data['port'])
        self.assertEqual(None, response.data['box'])

        # port
        base_url = reverse('net_link-api:link-element-detail',kwargs={'id': port_element_id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['type'], Element.Type.DISTRIFRAME_PORT)
        self.assertKeysIn([
            'id', 'number', 'row', 'col', 'distribution_frame', 'is_linked', 'element_id', 'link_id'
        ], response.data['port'])
        self.assertKeysIn([
            'id', 'number'
        ], response.data['port']['distribution_frame'])
        self.assertEqual(port_element_id, response.data['port']['element_id'])
        self.assertEqual(None, response.data['fiber'])
        self.assertEqual(None, response.data['lease'])
        self.assertEqual(None, response.data['box'])

        # box
        base_url = reverse('net_link-api:link-element-detail',kwargs={'id': box_element_id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['type'], Element.Type.CONNECTOR_BOX)
        self.assertKeysIn([
            'id', 'number', 'place', 'remarks', 'location', 'place', 'is_linked', 'element_id', 'link_id'
        ], response.data['box'])
        self.assertEqual(box_element_id, response.data['box']['element_id'])
        self.assertEqual(None, response.data['fiber'])
        self.assertEqual(None, response.data['lease'])
        self.assertEqual(None, response.data['port'])

