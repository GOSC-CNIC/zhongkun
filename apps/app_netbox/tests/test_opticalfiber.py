from urllib import parse
from datetime import date

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.app_net_link.managers.link import FiberCableManager, LinkManager
from apps.app_net_link.managers.common import NetLinkUserRoleWrapper as NetBoxUserRoleWrapper
from apps.app_net_link.models import OpticalFiber, Link
from apps.app_net_link.permissions import LinkIPRestrictor


class OpticalFiberTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')

        u2_roler = NetBoxUserRoleWrapper(self.user2)
        u2_roler.user_role = u2_roler.get_or_create_user_role()
        u2_roler.set_link_readonly(True)

        u3_roler = NetBoxUserRoleWrapper(self.user3)
        u3_roler.user_role = u3_roler.get_or_create_user_role()
        u3_roler.set_link_admin(True)

        self.cable1 = FiberCableManager.create_fibercable(
            number='SM-test',
            fiber_count=30,
            length=30.5,
            endpoint_1='软件园',
            endpoint_2='古脊椎',
            remarks='test-remark'
        )
        LinkIPRestrictor.add_ip_rule(ip_value='0.0.0.0/0')
        LinkIPRestrictor.clear_cache()
        
    def test_list_opticalfiber(self):
        # user role 
        base_url = reverse('netbox-api:link-opticalfiber-list')
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
        self.assertEqual(response.data['count'], 30)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 20)
        opticalfiber = response.data['results'][0]
        self.assertKeysIn([
            'id', 'sequence', 'fiber_cable', 'is_linked', 'element_id', 'link_id'
        ], opticalfiber)
        self.assertKeysIn([
            'id', 'number'
        ], opticalfiber['fiber_cable'])
        id = opticalfiber['id']
        db_opticalfiber = OpticalFiber.objects.filter(id=id).first()
        self.assertEqual(opticalfiber['sequence'], db_opticalfiber.sequence)
        self.assertEqual(opticalfiber['fiber_cable']['id'], db_opticalfiber.fiber_cable.id)
        self.assertEqual(opticalfiber['fiber_cable']['number'], db_opticalfiber.fiber_cable.number)
        self.assertEqual(opticalfiber['is_linked'], False)
        self.assertEqual(opticalfiber['element_id'], db_opticalfiber.element.id)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 2})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 30)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)

        # query "is_linked" "link_id"
        query = parse.urlencode(query={'is_linked': '1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'is_linked': 'False'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['is_linked'], False)
        opticalfiber = OpticalFiber.objects.all().first()
        link = LinkManager.create_link(
            number="KY23092702",
            user="空天院-中国遥感卫星地面站",
            endpoint_a="空天院新技术园区B座A301机房，王萌13811835852",
            endpoint_z="海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈"
                       "老师13810428468，布跳线联系徐工13521066224",
            bandwidth=0,
            description="中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            line_type="科技云科技专线",
            business_person="周建虎",
            build_person="胡亮亮、王振伟",
            link_status=Link.LinkStatus.USING,
            remarks="adaeda",
            enable_date=date(year=2014, month=7, day=1),
            link_element=[
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfiber.element.id
                }
            ]
        )
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], opticalfiber.id)
        self.assertEqual(response.data['results'][0]['is_linked'], True)
        self.assertEqual(len(response.data['results'][0]['link_id']), 1)
        self.assertEqual(response.data['results'][0]['link_id'][0], link.id)

        # query "cable_id"
        query = parse.urlencode(query={'cable_id': 'abc'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        query = parse.urlencode(query={'cable_id': self.cable1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], self.cable1.fiber_count)
