from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.leaseline_manager import LeaseLineManager
from link.managers.elementlink_manager import ElementLinkManager
from datetime import date
from django.urls import reverse
from link.models import LeaseLine, Element, ElementLink
from link.managers.userrole_manager import UserRoleWrapper
from urllib import parse

class LeaseLineTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        UserRoleWrapper(user=self.user2).add_read_permission()
        UserRoleWrapper(user=self.user3).add_write_permission()
        LeaseLineManager.create_leaseline(
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
        LeaseLineManager.create_leaseline(
            private_line_number='26001927719',
            lease_line_code='',
            line_username='国家气象中心云岗通信台',
            endpoint_a='北京市海淀区中关村南四街4号',
            endpoint_z='',
            line_type='接入网',
            cable_type='MSTP电路',
            bandwidth=170,
            length=None,
            provider='移动（北京）',
            enable_date=date.fromisoformat('2014-11-22'),
            is_whithdrawal=True,
            money=300.20,
            remarks=''
        )

    def test_creat(self):       
        base_url = reverse('api:link-leaseline-list')
        data = {
            'private_line_number':'510GXN12603174',
            'lease_line_code':'0F0001NP',
            'line_username':'广州联通互联互通',
            'endpoint_a':'广州市天河乐意居广州化学所',
            'endpoint_z':'广州联通科学城2数据机房',
            'line_type':'骨干网',
            'cable_type':'裸光纤',
            'bandwidth':'400',
            'length':'',
            'provider':'联通（北京）',
            'enable_date':'2023-06-15',
            'is_whithdrawal':'false',
            'money':'300.20',
            'remarks':'电路编号：中科院广州化学有限公司-科学城2数据机房0F0001NP'
            }
        
        # user role 
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user3)
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)
        
        # data
        leaseline = response.data
        self.assertKeysIn([
            'id', 'private_line_number', 'lease_line_code', 'line_username', 'endpoint_a', 'endpoint_z',
            'line_type', 'cable_type', 'bandwidth', 'length', 'provider', 'enable_date', 'is_whithdrawal',
            'money', 'remarks', 'is_linked'
        ], leaseline)
        self.assertEqual(response.data['private_line_number'], '510GXN12603174')
        self.assertEqual(response.data['lease_line_code'], '0F0001NP')
        leaseline = LeaseLine.objects.filter(private_line_number='510GXN12603174').first()
        self.assertEqual(leaseline.element.object_type, Element.Type.LEASE_LINE)
        self.assertEqual(leaseline.element.object_id, leaseline.id)
        self.assertEqual(leaseline.element.element_leaseline.id, leaseline.id)

    def test_list(self):
        # user role 
        base_url = reverse('api:link-leaseline-list')
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

        # data
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)
        leaseline = response.data['results'][0]
        self.assertKeysIn([
            'id', 'private_line_number', 'lease_line_code', 'line_username', 'endpoint_a', 'endpoint_z',
            'line_type', 'cable_type', 'bandwidth', 'length', 'provider', 'enable_date', 'is_whithdrawal',
            'money', 'remarks', 'is_linked'
        ], leaseline)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # query 'is_whithdrawal'
        query = parse.urlencode(query={'is_whithdrawal': '1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'is_whithdrawal': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['is_whithdrawal'], True)

        # query "search"
        query = parse.urlencode(query={'search': '南京'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        query = parse.urlencode(query={'search': '天津空港物流'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        query = parse.urlencode(query={'search': '天津空港物流', 'is_whithdrawal': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        # query "enable_date"
        query = parse.urlencode(query={'enable_date_start': '2017.07.14'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'enable_date_start': '2003-07-14'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        query = parse.urlencode(query={'enable_date_start': '2017-07-14'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        query = parse.urlencode(query={'enable_date_start': '2023-10-26'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        query = parse.urlencode(query={'enable_date_start': '2023-10-26', 'enable_date_end': '2021-10-26'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'enable_date_start': '2003-07-14', 'enable_date_end': '2017-07-14'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        # verify is_linked
        leaseline_list = list(LeaseLine.objects.all())
        ElementLinkManager.create_elementlink(
            number="test_link",
            elements=[
                {'object_type':'lease-line', 'object_id': leaseline_list[0].id},
                {'object_type':'lease-line', 'object_id': leaseline_list[1].id}
            ],
            remarks="test_remarks",
            link_status=ElementLink.LinkStatus.IDLE,
            task=None
        )
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        leaseline = response.data['results'][0]
        self.assertEqual(response.data['results'][0]['is_linked'], True)
        self.assertEqual(response.data['results'][1]['is_linked'], True)

    def test_update(self):       
        base_url = reverse('api:link-leaseline-update-leaseline', kwargs={'id': 'test'})
        data = {
            'private_line_number':'510GXN12603174',
            'lease_line_code':'0F0001NP',
            'line_username':'广州联通互联互通',
            'endpoint_a':'广州市天河乐意居广州化学所',
            'endpoint_z':'广州联通科学城2数据机房',
            'line_type':'骨干网',
            'cable_type':'裸光纤',
            'bandwidth':'400',
            'length':'',
            'provider':'联通（北京）',
            'enable_date':'2023-06-15',
            'is_whithdrawal':'false',
            'money':'300.20',
            'remarks':'电路编号：中科院广州化学有限公司-科学城2数据机房0F0001NP'
            }
        
        # user role
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user3)
        response = self.client.post(base_url, data=data)

        # LeaseLineNotExist
        self.assertErrorResponse(status_code=404, code='LeaseLineNotExist', response=response)
        id = LeaseLine.objects.all().first().id
        base_url = reverse('api:link-leaseline-update-leaseline', kwargs={'id': id})
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)

        # data
        leaseline = response.data
        self.assertKeysIn([
            'id', 'private_line_number', 'lease_line_code', 'line_username', 'endpoint_a', 'endpoint_z',
            'line_type', 'cable_type', 'bandwidth', 'length', 'provider', 'enable_date', 'is_whithdrawal',
            'money', 'remarks', 'is_linked'
        ], leaseline)
        self.assertEqual(response.data['private_line_number'], '510GXN12603174')
        self.assertEqual(response.data['lease_line_code'], '0F0001NP')
        leaseline = LeaseLine.objects.filter(private_line_number='510GXN12603174').first()
        self.assertEqual(leaseline.element.object_type, Element.Type.LEASE_LINE)
        self.assertEqual(leaseline.element.object_id, leaseline.id)

